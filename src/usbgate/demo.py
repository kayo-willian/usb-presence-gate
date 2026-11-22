"""Opt-in USB presence gate for one project-owned disposable service.

Not a general-purpose service gate and not cryptographic authentication.
Only presence-demo.service may be started or stopped. Never touch SSH,
network, firewall, Docker or third-party systemd members.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time

POLICY = Path("/etc/usbgate/demo.json")
GRANT = Path("/run/usbgate/demo-grant")
UNIT = Path("/etc/systemd/system/presence-demo.service")
SERVICE = "presence-demo.service"
RULE = Path("/etc/udev/rules.d/70-usbgate.rules")
TIMER = "usbgate-reconcile.timer"
MANIFEST = Path("/var/lib/usbgate/install-manifest.json")
IDENTIFIER = re.compile(r"^[a-f0-9]{12}$")


def require_root():
    if os.geteuid() != 0:
        raise RuntimeError("demo operations require root")


def systemctl(*args, check=True):
    return subprocess.run(["/usr/bin/systemctl", *args], check=check,
                          capture_output=True, text=True, timeout=15)


def service_active():
    return systemctl("is-active", SERVICE, check=False).stdout.strip() == "active"


def timer_active():
    return systemctl("is-active", TIMER, check=False).stdout.strip() == "active"


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
        raise RuntimeError("demo systemd unit fails safety preflight") from error


def revoke():
    if GRANT.is_symlink():
        raise RuntimeError("grant symlink refused")
    GRANT.unlink(missing_ok=True)


def stop_demo():
    """Stop and verify only the project-owned disposable service."""
    systemctl("stop", SERVICE)
    if service_active():
        raise RuntimeError("demo service still active after stop")


def close_demo():
    revoke()
    stop_demo()


def open_grant():
    if GRANT.is_symlink():
        raise RuntimeError("grant symlink refused")
    GRANT.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if GRANT.parent.is_symlink() or (GRANT.parent.stat().st_mode & 0o077):
        raise RuntimeError("unsafe runtime directory")
    if GRANT.exists():
        return False
    fd = os.open(GRANT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    return True


def key_present(policy, observations):
    observed = observations.get(policy["fingerprint"])
    return bool(observed and observed.get("assurance") == "identifier-only"
                and "08" in observed.get("classes", []))


def reconcile(state, observations):
    """Called by the root observation worker under its shared flock."""
    try:
        policy = read_policy()
    except RuntimeError:
        close_demo()  # fail closed on corrupted/unsafe applied policy
        raise
    if policy is None:
        if GRANT.exists() or GRANT.is_symlink():
            close_demo()
        return
    if not policy["enabled"]:
        if GRANT.exists() or GRANT.is_symlink():
            close_demo()
        return
    try:
        verify_unit()
        if not RULE.is_file() or not timer_active():
            raise RuntimeError("safety monitor unavailable")
        observed = key_present(policy, observations)
        record = state.get("devices", {}).get(policy["fingerprint"], {})
        transition = record.get("state")
        if observed and transition == "present":
            # A live grant is opened only after verifying a currently visible
            # unique storage identifier and the active safety timer.
            if open_grant():
                systemctl("start", SERVICE)
                if not service_active():
                    raise RuntimeError("demo start not active")
        elif transition == "pending" and GRANT.is_file():
            # Allow at most the persisted 10-second observation grace.
            return
        else:
            close_demo()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        close_demo()
        raise


def lock_and_run(operation, *args):
    """Mutations share the observation lock; avoid concurrent grant decisions."""
    require_root()
    from .cli import LOCK, RUNTIME
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    if RUNTIME.is_symlink():
        raise RuntimeError("runtime symlink refused")
    with LOCK.open("a+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
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
    from .cli import devices, boot_id, STATE
    from .observe import advance
    policy = read_policy()
    if not policy:
        raise RuntimeError("enroll a USB fingerprint before enabling")
    if policy["enabled"]:
        raise RuntimeError("demo is already enabled")
    verify_unit()
    if not RULE.is_file() or not timer_active():
        raise RuntimeError("enable USB observation and its safety timer first")
    if service_active():
        raise RuntimeError("demo service already active; refusing unmanaged takeover")
    current = devices()
    if not key_present(policy, current):
        raise RuntimeError("enrolled USB device must be present and unambiguous")
    save_policy(dict(policy, enabled=True))
    state, _, _ = advance({}, set(current), time.clock_gettime(time.CLOCK_BOOTTIME), boot_id())
    reconcile(state, current)
    print("Demo gate enabled for the disposable presence-demo.service only.")


def disable():
    policy = read_policy()
    if policy is None:
        raise RuntimeError("demo not enrolled")
    close_demo()
    save_policy(dict(policy, enabled=False))
    print("Demo gate disabled; disposable service stopped.")


def reset():
    policy = read_policy()
    if policy is None:
        raise RuntimeError("demo not enrolled")
    if policy["enabled"]:
        raise RuntimeError("disable the demo gate before reset")
    if GRANT.exists() or GRANT.is_symlink() or service_active():
        raise RuntimeError("grant or demo activity remains; refuse reset")
    POLICY.unlink()
    print("Demo enrollment removed; no service affected.")


def status():
    try:
        policy = read_policy()
        state = "enabled" if policy and policy["enabled"] else ("enrolled" if policy else "unconfigured")
    except RuntimeError:
        state = "corrupt (recovery required)"
    return {
        "state": state,
        "service": SERVICE,
        "grant_file": GRANT.is_file(),
        "service_active": service_active(),
        "no_general_service_control": True,
    }
