"""Read-only USB observer and explicit observation lifecycle."""
from contextlib import contextmanager
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import syslog
import tempfile
import time
from . import __version__
from .observe import advance
from .policy import inspect_unit, unit_state

SYSFS = Path("/sys/bus/usb/devices")
RUNTIME = Path("/run/usbgate")
STATE = RUNTIME / "observe.json"
LOCK = RUNTIME / "lock"
RULE = Path("/etc/udev/rules.d/70-usbgate.rules")
SOURCE_RULE = Path("/usr/local/lib/usbgate/packaging/udev/70-usbgate.rules")
TIMER = "usbgate-reconcile.timer"
SERVICE = "usbgate-reconcile.service"
SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def read_attribute(path):
    try:
        raw = path.read_bytes()
        value = raw.decode("ascii", "strict").strip() if len(raw) <= 128 else ""
        return value if SAFE.fullmatch(value) else ""
    except (OSError, UnicodeError, ValueError):
        return ""


def devices(root=SYSFS):
    """Only sysfs descriptors; never mount or open a USB filesystem."""
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)[:512]
    except OSError:
        return {}
    classes = {}
    for entry in entries:
        if ":" not in entry.name:
            continue
        key = entry.name.split(":", 1)[0]
        kind = read_attribute(entry / "bInterfaceClass")
        if re.fullmatch(r"[0-9A-Fa-f]{2}", kind):
            classes.setdefault(key, set()).add(kind.lower())
    result = {}
    for entry in entries:
        if not re.fullmatch(r"[0-9]+-[0-9.]+", entry.name):
            continue
        vid, pid, serial = (read_attribute(entry / name) for name in ("idVendor", "idProduct", "serial"))
        if not re.fullmatch(r"[a-fA-F0-9]{4}", vid) or not re.fullmatch(r"[a-fA-F0-9]{4}", pid):
            continue
        key = hashlib.sha256(f"{vid.lower()}:{pid.lower()}:{serial}".encode("ascii")).hexdigest()[:12]
        if key in result:
            # One descriptor fingerprint cannot prove which physical device is present.
            # Keep the group visible, but never claim a unique identity.
            existing = result[key]
            if existing["assurance"] != "ambiguous":
                existing["buses"] = [existing.pop("bus")]
                existing["assurance"] = "ambiguous"
            existing["buses"].append(entry.name)
            existing["buses"].sort()
            existing["instances"] = len(existing["buses"])
            existing["classes"] = sorted(set(existing["classes"]) | classes.get(entry.name, set()))
            continue
        result[key] = {"bus": entry.name, "vid_pid": f"{vid.lower()}:{pid.lower()}",
                       "classes": sorted(classes.get(entry.name, set())),
                       "assurance": "identifier-only" if serial else "weak"}
    return result


def boot_id():
    return read_attribute(Path("/proc/sys/kernel/random/boot_id")) or "unknown"


def load_state():
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("devices"), dict):
            return {}
        for key, item in data["devices"].items():
            if not re.fullmatch(r"[a-f0-9]{12}", key) or not isinstance(item, dict):
                return {}
            if item.get("state") not in ("present", "pending", "absent"):
                return {}
        return data
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def save_state(data):
    RUNTIME.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".observe-", dir=RUNTIME)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, STATE)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def record_observation(previous, observations, now, current_boot, grace=10):
    """Commit a sample under the caller's lock before it can authorize a start."""
    from . import demo
    state, events, remaining = advance(previous, set(observations), now, current_boot, grace)
    try:
        save_state(state)
    except (OSError, ValueError, TypeError) as exc:
        demo.close_after_error("could not persist USB observation", exc)
    for event, fingerprint in events:
        syslog.openlog(ident="usbgate")
        syslog.syslog(syslog.LOG_INFO, f"event={event} fingerprint={fingerprint} mode=observe")
    return state, remaining


@contextmanager
def locked(path):
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    if RUNTIME.is_symlink():
        raise RuntimeError("runtime symlink refused")
    with path.open("a+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield


def observe_once(grace=10, scan=None, clock=None, delay=None, current_boot=None):
    """Persist first absence; wait its remainder; rescan even without new USB events."""
    from . import demo
    scan = scan or devices
    clock = clock or (lambda: time.clock_gettime(time.CLOCK_BOOTTIME))
    delay = delay or time.sleep
    current_boot = current_boot or boot_id()
    with locked(LOCK):
        previous = load_state()
        for _ in range(3):
            found = scan()
            observations = found if isinstance(found, dict) else {key: {} for key in found}
            state, remaining = record_observation(previous, observations, clock(), current_boot, grace)
            demo.reconcile(state, observations)
            if remaining is None:
                return state
            previous = state
            delay(remaining)
        return state


def timer_active():
    try:
        state = unit_state(TIMER)
    except RuntimeError:
        return None
    return {"active": True, "inactive": False}.get(state)


def has_enrollment():
    for pattern in ("*.service.d", "*.socket.d"):
        for directory in Path("/etc/systemd/system").glob(pattern):
            if (directory / "50-usbgate.conf").exists():
                return True
    return False


def monitor(enable):
    from . import demo
    demo.require_root()
    with locked(RUNTIME / "admin.lock"):
        with locked(LOCK):
            policy = demo.read_policy()
            armed = policy and policy["enabled"]
            if armed and (not enable or demo.inhibited()):
                raise RuntimeError("disable the demo gate before changing USB observation")
            if not enable and has_enrollment():
                raise RuntimeError("policy drop-ins detected; refusing to disable observation")
            if armed:
                try:
                    demo.verify_monitor()
                except RuntimeError as exc:
                    context = "armed monitor verification failed"
                    try:
                        demo.inhibit()
                    except (OSError, RuntimeError) as marker_error:
                        context += f"; could not inhibit authorization: {marker_error}"
                    demo.close_after_error(context, exc)
                print("Observation enabled.")
                return
            demo.inhibit()
            try:
                demo.close_demo()
            except RuntimeError as exc:
                raise RuntimeError(f"monitor transition inhibited: {exc}; retry after recovery") from exc
        # A worker started or stopped below can take LOCK; it never takes admin.lock.
        try:
            rule_content = demo.installed_bytes(SOURCE_RULE)
            if enable and (RULE.exists() or RULE.is_symlink()):
                demo.verify_rule()
            configure_monitor(enable, rule_content)
            with locked(LOCK):
                target = "active" if enable else "inactive"
                if unit_state(TIMER) != target or RULE.exists() != enable:
                    raise RuntimeError("monitor configuration unconfirmed")
                if enable:
                    demo.verify_monitor()
                else:
                    if unit_state(SERVICE) != "inactive":
                        raise RuntimeError("observer shutdown unconfirmed")
                    demo.close_demo()
                demo.INHIBIT.unlink()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            raise RuntimeError(f"monitor transition incomplete: {exc}; authorization inhibited; "
                               "retry monitor setup or shutdown") from exc
    print("Observation enabled." if enable else "Observation disabled.")


def configure_monitor(enable, rule_content):
    errors = []
    if enable:
        from . import demo
        subprocess.run(["/usr/bin/systemctl", "daemon-reload"], capture_output=True, text=True,
                       check=True, timeout=30)
        demo.verify_timer(operational=False)
        if not RULE.exists():
            fd = os.open(RULE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as stream:
                stream.write(rule_content)
        actions = [
            ("/usr/bin/udevadm", "control", "--reload"),
            ("/usr/bin/systemctl", "enable", "--now", TIMER),
            ("/usr/bin/systemctl", "start", SERVICE),
        ]
    else:
        from . import demo
        demo.verify_timer(operational=False)
        actions = [
            ("/usr/bin/systemctl", "disable", "--now", TIMER),
        ]
        if RULE.is_symlink():
            errors.append("udev rule symlink left in place")
        elif RULE.exists():
            if demo.trusted_bytes(RULE) != rule_content:
                errors.append("modified udev rule left in place")
            else:
                RULE.unlink()
        actions.extend([("/usr/bin/udevadm", "control", "--reload"),
                        ("/usr/bin/systemctl", "stop", SERVICE)])
    for args in actions:
        try:
            subprocess.run(args, capture_output=True, text=True, check=True, timeout=30)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{args[0]} {args[1]}: {exc}")
            if enable:
                break
    if errors:
        raise RuntimeError("; ".join(errors))


def status(json_mode=False):
    state = load_state()
    from .demo import status as demo_status
    demo = demo_status()
    mode = "observe" if RULE.exists() else "inert"
    output = {"mode": "inhibited" if demo["authorization_inhibited"] else mode,
              "timer_active": timer_active(),
              "monitor_safety": monitor_diagnostic(),
              "enforcement": demo["state"] == "enabled" and not demo["authorization_inhibited"],
              "demo": demo,
              "boot_id_match": state.get("boot_id") == boot_id(),
              "devices": state.get("devices", {})}
    if json_mode:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(f"Mode: {output['mode']}; timer active: {output['timer_active']}")
        for key, item in sorted(output["devices"].items()):
            print(f"  {key}: {item['state']}")


def monitor_diagnostic():
    from . import demo
    try:
        demo.verify_monitor()
    except RuntimeError as exc:
        return str(exc)
    return "verified"


def doctor():
    checks = {"python": sys.version.split()[0],
              "systemd_running": Path("/run/systemd/system").exists(),
              "usb_sysfs": SYSFS.is_dir(),
              "package_installed": SOURCE_RULE.is_file(),
              "observer_enabled": RULE.is_file(),
              "monitor_safety": monitor_diagnostic(),
              "timer_active": timer_active(),
              "state_available": STATE.exists()}
    for key, value in checks.items():
        print(f"{key}: {value}")
    print("USB descriptors are not authentication; demo control requires explicit enrollment.")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="usbgate", description="USB presence observer (not authentication)")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("scan", help="Read current USB descriptors without raw serials")
    sub.add_parser("doctor", help="Read-only host checks")
    p = sub.add_parser("inspect-unit", help="Read-only candidate review; never enrolls")
    p.add_argument("unit", help="Canonical locally managed .service or .socket unit")
    p = sub.add_parser("status", help="Read the observation cache")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("monitor", help="Enable or disable observation only")
    p.add_argument("mode", choices=("enable", "disable"))
    p = sub.add_parser("demo", help="Opt-in control of one disposable demo service only")
    p.add_argument("mode", choices=("enroll", "enable", "disable", "reset", "status"))
    p.add_argument("fingerprint", nargs="?")
    p = sub.add_parser("reconcile", help="Internal observation worker")
    p.add_argument("--observe", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "scan":
            print(json.dumps(devices(), indent=2, sort_keys=True))
        elif args.action == "doctor":
            doctor()
        elif args.action == "inspect-unit":
            print(json.dumps(inspect_unit(args.unit), indent=2, sort_keys=True))
        elif args.action == "status":
            status(args.json)
        elif args.action == "monitor":
            monitor(args.mode == "enable")
        elif args.action == "demo":
            from . import demo
            if args.mode == "status":
                print(json.dumps(demo.status(), indent=2, sort_keys=True))
            else:
                if args.mode == "enroll":
                    if args.fingerprint is None:
                        raise ValueError("demo enroll requires a fingerprint")
                    demo.lock_and_run(demo.enroll, args.fingerprint)
                else:
                    if args.fingerprint is not None:
                        raise ValueError("only demo enroll accepts a fingerprint")
                    demo.lock_and_run(getattr(demo, args.mode))
        elif args.action == "reconcile":
            if os.geteuid() != 0:
                raise RuntimeError("reconcile requires root")
            observe_once()
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"usbgate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
