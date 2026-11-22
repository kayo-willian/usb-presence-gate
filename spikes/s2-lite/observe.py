"""One-shot S2-lite port observation. All results go to the journal via stdout."""

import fcntl
import os
import re
import stat
import sys
import time
from pathlib import Path

USB_DEVICES = Path("/sys/bus/usb/devices")
STATE = Path("/run/usbgate-s2-lite")
GRACE_NS = 5_000_000_000  # Fixture interval only.


def boot_ns():
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def report(event, **fields):
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    print(f"event={event} boot_ns={boot_ns()} {details}".rstrip(), flush=True)


def read_absence(marker):
    try:
        fd = os.open(marker, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError("unsafe absence marker")
        value = source.read(32)
        if not re.fullmatch(rb"[0-9]{1,20}\n", value):
            raise ValueError("invalid absence marker")
        return int(value)


def observe(state, present, clock, sleep, log):
    marker = state / "absent_since"
    if present():
        marker.unlink(missing_ok=True)
        log("complete", present=1)
        return

    since = read_absence(marker)
    now = clock()
    if since is None:
        since = now
        # A restart may interrupt this write. Only the renamed file is authoritative.
        pending = state / "absent_since.next"
        pending.unlink(missing_ok=True)
        fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as output:
            output.write(f"{since}\n")
            output.flush()
            os.fsync(output.fileno())
        pending.replace(marker)
    if since > now:
        raise ValueError("absence marker is in the future")
    deadline = since + GRACE_NS
    log("absent", since_ns=since, deadline_ns=deadline)
    while (remaining := deadline - clock()) > 0:
        sleep(remaining / 1_000_000_000)
    returned = present()
    if returned:
        marker.unlink(missing_ok=True)
    log("complete", present=int(returned), rescan=1, since_ns=since)


def main():
    port = os.environ.get("SPIKE_PORT", "")
    if not re.fullmatch(r"[1-9][0-9]*-[1-9][0-9]*(?:\.[1-9][0-9]*)*", port):
        raise ValueError("expected a kernel USB port location")
    # Only compare names supplied by sysfs. Never construct a path from port.
    def present():
        return port in os.listdir(USB_DEVICES)

    directory = os.open(STATE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(directory)
        if info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError("unsafe runtime directory")
        fcntl.flock(directory, fcntl.LOCK_EX)
        report("begin")
        observe(STATE, present, boot_ns, time.sleep, report)
    finally:
        os.close(directory)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f"observation_failed={type(exc).__name__}", file=sys.stderr)
        sys.exit(1)
