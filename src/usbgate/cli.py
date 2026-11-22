"""Read-only USB observer and explicit observation lifecycle."""
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


def observe_once(grace=10, scan=None, clock=None, delay=None, current_boot=None):
    """Persist first absence; wait its remainder; rescan even without new USB events."""
    scan = scan or (lambda: set(devices()))
    clock = clock or (lambda: time.clock_gettime(time.CLOCK_BOOTTIME))
    delay = delay or time.sleep
    current_boot = current_boot or boot_id()
    RUNTIME.mkdir(parents=True, mode=0o700, exist_ok=True)
    with LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = load_state()
        for _ in range(3):
            state, events, remaining = advance(previous, scan(), clock(), current_boot, grace)
            save_state(state)
            for event, fingerprint in events:
                syslog.openlog(ident="usbgate")
                syslog.syslog(syslog.LOG_INFO, f"event={event} fingerprint={fingerprint} mode=observe")
            if remaining is None:
                return state
            previous = state
            delay(remaining)
        return state


def command(*args, check=True):
    return subprocess.run(["/usr/bin/systemctl", *args], check=check,
                          capture_output=True, text=True, timeout=20)


def timer_active():
    try:
        return command("is-active", TIMER, check=False).stdout.strip() == "active"
    except (OSError, subprocess.TimeoutExpired):
        return False


def has_enrollment():
    for pattern in ("*.service.d", "*.socket.d"):
        for directory in Path("/etc/systemd/system").glob(pattern):
            if (directory / "50-usbgate.conf").exists():
                return True
    return False


def monitor(enable):
    if os.geteuid() != 0:
        raise RuntimeError("monitor requires root")
    if not SOURCE_RULE.is_file():
        raise RuntimeError("install the tool first with sudo make install")
    if not enable and has_enrollment():
        raise RuntimeError("policy drop-ins detected; refusing to disable observation")
    errors = []
    if enable:
        if RULE.is_symlink():
            raise RuntimeError("udev rule is a symlink")
        content = SOURCE_RULE.read_bytes()
        if RULE.exists() and RULE.read_bytes() != content:
            raise RuntimeError("udev rule differs from project-owned file")
        if not RULE.exists():
            fd = os.open(RULE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
        actions = [
            ("/usr/bin/systemctl", "daemon-reload"),
            ("/usr/bin/udevadm", "control", "--reload"),
            ("/usr/bin/systemctl", "enable", "--now", TIMER),
            ("/usr/bin/systemctl", "start", SERVICE),
        ]
    else:
        actions = [
            ("/usr/bin/systemctl", "disable", "--now", TIMER),
            ("/usr/bin/systemctl", "stop", SERVICE),
        ]
        if RULE.is_symlink():
            errors.append("udev rule symlink left in place")
        elif RULE.exists():
            if RULE.read_bytes() != SOURCE_RULE.read_bytes():
                errors.append("modified udev rule left in place")
            else:
                RULE.unlink()
        actions.append(("/usr/bin/udevadm", "control", "--reload"))
    for args in actions:
        try:
            subprocess.run(args, capture_output=True, text=True, check=True, timeout=30)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{args[0]} {args[1]}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    print("Observation enabled; no service control." if enable else "Observation disabled.")


def status(json_mode=False):
    state = load_state()
    output = {"mode": "observe" if RULE.exists() else "inert",
              "timer_active": timer_active(), "enforcement": False,
              "boot_id_match": state.get("boot_id") == boot_id(),
              "devices": state.get("devices", {})}
    if json_mode:
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(f"Mode: {output['mode']}; timer active: {output['timer_active']}")
        for key, item in sorted(output["devices"].items()):
            print(f"  {key}: {item['state']}")


def doctor():
    checks = {"python": sys.version.split()[0],
              "systemd_running": Path("/run/systemd/system").exists(),
              "usb_sysfs": SYSFS.is_dir(),
              "package_installed": SOURCE_RULE.is_file(),
              "observer_enabled": RULE.is_file(),
              "timer_active": timer_active(),
              "state_available": STATE.exists()}
    for key, value in checks.items():
        print(f"{key}: {value}")
    print("Observation only; no enrollment, authentication, or service control.")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="usbgate", description="USB presence observer (not authentication)")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("scan", help="Read current USB descriptors without raw serials")
    sub.add_parser("doctor", help="Read-only host checks")
    p = sub.add_parser("status", help="Read the observation cache")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("monitor", help="Enable or disable observation only")
    p.add_argument("mode", choices=("enable", "disable"))
    p = sub.add_parser("reconcile", help="Internal observation worker")
    p.add_argument("--observe", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "scan":
            print(json.dumps(devices(), indent=2, sort_keys=True))
        elif args.action == "doctor":
            doctor()
        elif args.action == "status":
            status(args.json)
        elif args.action == "monitor":
            monitor(args.mode == "enable")
        elif args.action == "reconcile":
            if os.geteuid() != 0:
                raise RuntimeError("reconcile requires root")
            observe_once()
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"usbgate: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
