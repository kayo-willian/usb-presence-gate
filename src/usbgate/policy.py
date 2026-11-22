"""Read-only unit preflight; never enrolls, starts, or stops a unit."""
import re
import subprocess

UNIT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,125}\.(service|socket)$")
DENY_EXACT = frozenset({
    "ssh", "sshd", "dbus", "networking", "ufw", "nftables",
    "apparmor", "auditd", "chrony", "ntp", "netfilter-persistent",
    "docker", "containerd",
})
DENY_PREFIX = (
    "ssh", "sshd", "systemd-", "dbus", "network", "wpa_supplicant",
    "getty", "serial-getty", "console-getty", "user", "rescue", "emergency",
    "iptables", "nftables", "ufw", "netfilter", "fail2ban",
    "apparmor", "auditd", "rsyslog", "chrony", "ntp", "usbgate-",
    "docker", "containerd",
)
FIELDS = (
    "Id", "Names", "LoadState", "FragmentPath", "CanStop",
    "DropInPaths", "PartOf", "BoundBy", "PropagatesStopTo",
    "StopPropagatedFrom", "OnFailure", "TriggeredBy", "Triggers",
    "ConsistsOf", "Conflicts",
)
STOP_RISK = (
    "PartOf", "BoundBy", "PropagatesStopTo", "StopPropagatedFrom",
    "OnFailure", "TriggeredBy", "Triggers", "ConsistsOf",
)


def validate_name(name):
    if not isinstance(name, str) or not UNIT.fullmatch(name):
        raise ValueError("only plain .service or .socket unit names are accepted")
    base = name.rsplit(".", 1)[0].lower()
    if base in DENY_EXACT or any(base.startswith(p) for p in DENY_PREFIX):
        raise ValueError("protected or potentially critical unit refused")
    return name


def inspect_unit(name, runner=subprocess.run):
    """Read effective manager metadata, never authorize enforcement."""
    validate_name(name)
    cmd = ["/usr/bin/systemctl", "show", "--no-pager",
           "--property=" + ",".join(FIELDS), name]
    run = runner(cmd, check=False, capture_output=True, text=True, timeout=10)
    if run.returncode != 0:
        raise RuntimeError("could not inspect systemd unit")
    data = {}
    for line in run.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in FIELDS:
                data[key] = value
    if data.get("LoadState") != "loaded":
        raise ValueError("unit is not loaded")
    if data.get("Id") != name:
        raise ValueError("alias given; use the canonical unit name")
    aliases = data.get("Names", "").split()
    if not aliases or name not in aliases:
        raise ValueError("cannot verify all unit aliases")
    for alias in aliases:
        validate_name(alias)
    if not data.get("FragmentPath", "").startswith("/etc/systemd/system/"):
        raise ValueError("only locally managed unit files are candidates")
    if data.get("CanStop") != "yes":
        raise ValueError("unit not reported as stoppable")
    if data.get("DropInPaths", "").strip():
        raise ValueError("existing unit drop-ins require separate review")
    risks = [key for key in STOP_RISK if data.get(key, "").strip()]
    if set(data.get("Conflicts", "").split()) - {"shutdown.target"}:
        risks.append("Conflicts")
    if risks:
        raise ValueError("risky systemd relationships: " + ", ".join(risks))
    return {
        "unit": name,
        "preflight": "passed",
        "enrolled": False,
        "enforcement_ready": False,
        "notice": "Read-only preflight is not approval of full dependency and stop-action safety.",
    }
