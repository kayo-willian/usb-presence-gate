"""Opt-in USB presence gate for one project-owned disposable service.

Not a general-purpose service gate and not cryptographic authentication.
Only presence-demo.service may be started or stopped. Never touch SSH,
network, firewall, Docker or third-party systemd members.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

from .policy import unit_state

POLICY = Path("/etc/usbgate/demo.json")
GRANT = Path("/run/usbgate/demo-grant")
UNIT = Path("/etc/systemd/system/presence-demo.service")
SERVICE = "presence-demo.service"
RULE = Path("/etc/udev/rules.d/70-usbgate.rules")
TIMER = "usbgate-reconcile.timer"
MANIFEST = Path("/var/lib/usbgate/install-manifest.json")
INHIBIT = MANIFEST.with_name("authorization-inhibited")
IDENTIFIER = re.compile(r"^[a-f0-9]{12}$")


def require_root():
    if os.geteuid() != 0:
        raise RuntimeError("administrative operations require root")


def systemctl(*args, check=True):
    return subprocess.run(["/usr/bin/systemctl", *args], check=check,
                          capture_output=True, text=True, timeout=15)


def timer_active():
    return unit_state(TIMER) == "active"


def read_policy():
    if POLICY.is_symlink():
        raise RuntimeError("demo policy symlink refused")
    if not POLICY.exists():
        return None
    info = POLICY.stat()
    if not stat.S_ISREG(info.st_mode) or (info.st_mode & 0o077):
        raise RuntimeError("demo policy permissions invalid")
    if info.st_uid != os.geteuid():
        raise RuntimeError("demo policy ownership invalid")
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise RuntimeError("demo policy unreadable") from error
    if (not isinstance(policy, dict) or set(policy) != {"schema_version", "fingerprint", "enabled"}
            or policy["schema_version"] != 1
            or not isinstance(policy["fingerprint"], str)
            or not IDENTIFIER.fullmatch(policy["fingerprint"])
            or type(policy["enabled"]) is not bool):
        raise RuntimeError("demo policy invalid")
    return policy


def save_policy(policy):
    if POLICY.is_symlink():
        raise RuntimeError("demo policy symlink refused")
    if POLICY.parent.is_symlink():
        raise RuntimeError("demo policy directory symlink refused")
    POLICY.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if POLICY.parent.stat().st_mode & 0o077:
        raise RuntimeError("demo policy directory permissions invalid")
    fd, temporary = tempfile.mkstemp(prefix=".policy-", dir=POLICY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(policy, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, POLICY)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_unit():
    """Check the installed unit is the project-owned, unmodified demo."""
    if UNIT.is_symlink() or not UNIT.is_file() or MANIFEST.is_symlink():
        raise RuntimeError("demo unit or install manifest missing/unsafe")
    try:
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = record["files"][str(UNIT)]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError("demo install manifest invalid") from error
    if hashlib.sha256(UNIT.read_bytes()).hexdigest() != expected:
        raise RuntimeError("demo unit differs from installed version")
    from .policy import inspect_unit
    try:
        inspect_unit(SERVICE)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"demo systemd unit fails safety preflight: {error}") from error


def revoke():
    if GRANT.is_symlink():
        raise RuntimeError("grant symlink refused")
    GRANT.unlink(missing_ok=True)


def stop_demo(*, stop_allowed=True):
    """Stop only a verified unit, then check the manager even if stop failed."""
    errors = []
    try:
        state = unit_state(SERVICE)
    except RuntimeError as exc:
        state = "unknown"
        errors.append(str(exc))
    if state == "inactive":
        return
    if not stop_allowed:
        raise RuntimeError("; ".join([*errors, f"unsafe to stop; service state: {state}"]))
    try:
        verify_unit()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise RuntimeError("; ".join([*errors, f"unsafe to stop: {exc}; service state: {state}"])) from exc

    try:
        systemctl("stop", SERVICE)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        errors.append(f"stop request failed: {exc}")
    try:
        state = unit_state(SERVICE)
    except RuntimeError as exc:
        raise RuntimeError("; ".join([*errors, f"inactivity unconfirmed: {exc}"])) from exc
    if state != "inactive":
        errors.append(f"inactivity unconfirmed: service is {state}")
    elif errors:
        errors.append("service confirmed inactive")
    if errors:
        raise RuntimeError("; ".join(errors))


def close_demo(*, stop_allowed=True):
    """Report both grant and unit outcomes when closure is incomplete."""
    try:
        revoke()
    except (OSError, RuntimeError) as exc:
        grant_error = f"grant revocation failed: {exc}"
    else:
        grant_error = None
    try:
        stop_demo(stop_allowed=stop_allowed)
    except RuntimeError as exc:
        raise RuntimeError(f"{grant_error or 'grant absent'}; {exc}; recovery required") from exc
    if grant_error:
        raise RuntimeError(f"{grant_error}; service confirmed inactive; recovery required")


def close_after_error(context, cause, *, stop_allowed=True):
    try:
        close_demo(stop_allowed=stop_allowed)
    except RuntimeError as exc:
        outcome = str(exc)
    else:
        outcome = "grant absent; service confirmed inactive"
    raise RuntimeError(f"{context}: {cause}; {outcome}") from cause


def verify_before_open():
    try:
        verify_unit()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        close_after_error("unit safety verification failed; recovery required", exc, stop_allowed=False)


def inhibited():
    try:
        INHIBIT.lstat()
    except FileNotFoundError:
        return False
    return True


def inhibit():
    # Existence alone inhibits opens, including a marker left by a dead process.
    try:
        fd = os.open(INHIBIT, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if INHIBIT.is_symlink() or not INHIBIT.is_file():
            raise RuntimeError("unsafe authorization inhibit marker")
        return False
    os.close(fd)
    return True


def open_grant():
    if GRANT.is_symlink():
        raise RuntimeError("grant symlink refused")
    GRANT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if GRANT.parent.is_symlink() or (GRANT.parent.stat().st_mode & 0o077):
        raise RuntimeError("unsafe runtime directory")
    if GRANT.exists():
        if not GRANT.is_file():
            raise RuntimeError("invalid demo grant")
        return
    fd = os.open(GRANT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)


def key_present(policy, observations):
    observed = observations.get(policy["fingerprint"])
    return bool(observed and observed.get("assurance") == "identifier-only"
                and "08" in observed.get("classes", []))


def ensure_running():
    """Apply a committed, eligible observation under the worker lock."""
    state = unit_state(SERVICE)
    if state not in ("active", "inactive"):
        raise RuntimeError(f"demo start unsafe while service is {state}")
    open_grant()
    if state == "inactive":
        systemctl("start", SERVICE)
        if unit_state(SERVICE) != "active":
            raise RuntimeError("demo start not confirmed active")


def reconcile(state, observations):
    """Called by the root observation worker under its shared flock."""
    try:
        policy = read_policy()
        blocked = inhibited()
    except (RuntimeError, OSError) as exc:
        close_after_error("could not read demo authorization state", exc)
    if blocked or not policy or not policy["enabled"]:
        close_demo()
        return
    verify_before_open()
    try:
        if not RULE.is_file() or not timer_active():
            raise RuntimeError("safety monitor unavailable")
        observed = key_present(policy, observations)
        record = state.get("devices", {}).get(policy["fingerprint"], {})
        transition = record.get("state")
        if observed and transition == "present":
            ensure_running()
            return
        if (transition == "pending" and policy["fingerprint"] not in observations
                and GRANT.is_file()):
            # Allow at most the persisted 10-second observation grace.
            return
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        close_after_error("demo reconciliation failed", exc)
    close_demo()


def lock_and_run(operation, *args):
    """Mutations share the observation lock; avoid concurrent grant decisions."""
    require_root()
    from .cli import LOCK, RUNTIME, locked
    with locked(RUNTIME / "admin.lock"), locked(LOCK):
        return operation(*args)


def enroll(fingerprint):
    from .cli import devices
    if not IDENTIFIER.fullmatch(fingerprint):
        raise ValueError("invalid fingerprint")
    if read_policy() is not None:
        raise RuntimeError("demo already enrolled; disable and reset first")
    match = devices().get(fingerprint)
    if not match or match["assurance"] != "identifier-only" or "08" not in match["classes"]:
        raise ValueError("device must be a present, unambiguous USB storage device with serial")
    save_policy({"schema_version": 1, "fingerprint": fingerprint, "enabled": False})
    print("Demo identity enrolled; enforcement still disabled.")


def enable():
    from .cli import devices, boot_id, load_state, record_observation
    policy = read_policy()
    if not policy:
        raise RuntimeError("enroll a USB fingerprint before enabling")
    if inhibited():
        raise RuntimeError("authorization inhibited; complete monitor recovery first")
    if policy["enabled"]:
        raise RuntimeError("demo is already enabled")
    verify_before_open()
    if not RULE.is_file() or not timer_active():
        raise RuntimeError("enable USB observation and its safety timer first")
    if unit_state(SERVICE) != "inactive":
        raise RuntimeError("demo service must be confirmed inactive before enable")
    current = devices()
    if not key_present(policy, current):
        raise RuntimeError("enrolled USB device must be present and unambiguous")
    record_observation(load_state(), current, time.clock_gettime(time.CLOCK_BOOTTIME), boot_id())
    # Commit the armed policy last. A worker after an interrupted start sees
    # the previous disabled policy and closes any grant or process left behind.
    try:
        ensure_running()
        if not RULE.is_file() or not timer_active():
            raise RuntimeError("safety monitor unavailable after start")
        save_policy(dict(policy, enabled=True))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        try:
            disarm_and_close(policy)
        except RuntimeError as rollback:
            raise RuntimeError(f"enable failed: {exc}; rollback: {rollback}") from exc
        raise RuntimeError(f"enable failed: {exc}; policy disabled; grant absent; service confirmed inactive") from exc
    print("Demo gate enabled for the disposable presence-demo.service only.")


def disarm_and_close(policy):
    errors = []
    created = False
    blocked = False
    try:
        created = inhibit()
        blocked = True
    except (OSError, RuntimeError) as exc:
        errors.append(f"could not inhibit authorization: {exc}")
    try:
        save_policy(dict(policy, enabled=False))
        policy_result = "policy disabled"
    except (OSError, ValueError, RuntimeError) as exc:
        errors.append(f"disarm write failed: {exc}")
        try:
            stored = read_policy()
            armed = bool(stored and stored["enabled"])
            policy_result = "policy still armed" if armed else "policy disarmed"
        except (OSError, RuntimeError) as read_error:
            armed = True
            policy_result = f"policy may remain armed: {read_error}"
        if armed:
            errors.append("automatic startup inhibited" if blocked else "automatic startup may still be possible")
    try:
        close_demo()
        closure = "grant absent; service confirmed inactive"
    except RuntimeError as exc:
        closure = str(exc)
        errors.append("closure incomplete or reported an error")
    if errors:
        raise RuntimeError("; ".join([policy_result, closure, *errors]))
    # An earlier interrupted admin operation owns its veto until monitor recovery.
    if created:
        try:
            INHIBIT.unlink()
        except OSError as exc:
            raise RuntimeError(f"{policy_result}; {closure}; could not clear inhibit: {exc}") from exc


def disable():
    try:
        policy = read_policy()
    except (OSError, RuntimeError) as exc:
        try:
            inhibit()
        except (OSError, RuntimeError) as marker_error:
            context = f"could not inhibit: {marker_error}; future startup unknown"
        else:
            context = "automatic startup inhibited"
        close_after_error(f"could not disarm unreadable policy; {context}", exc)
    if policy is None:
        raise RuntimeError("demo not enrolled")
    disarm_and_close(policy)
    print("Demo gate disabled; disposable service stopped.")


def reset():
    policy = read_policy()
    if policy is None:
        raise RuntimeError("demo not enrolled")
    if policy["enabled"]:
        raise RuntimeError("disable the demo gate before reset")
    if GRANT.exists() or GRANT.is_symlink() or unit_state(SERVICE) != "inactive":
        raise RuntimeError("grant or demo activity remains; refuse reset")
    POLICY.unlink()
    print("Demo enrollment removed; no service affected.")


def status():
    try:
        policy = read_policy()
        state = "enabled" if policy and policy["enabled"] else ("enrolled" if policy else "unconfigured")
    except RuntimeError:
        state = "corrupt (recovery required)"
    try:
        service_state = unit_state(SERVICE)
        detail = {}
    except RuntimeError as exc:
        service_state = "unknown"
        detail = {"service_state_error": str(exc)}
    return {
        "state": state,
        "service": SERVICE,
        "authorization_inhibited": inhibited(),
        "grant_file": GRANT.is_file(),
        "service_state": service_state,
        "service_active": {"active": True, "inactive": False}.get(service_state),
        **detail,
        "no_general_service_control": True,
    }
