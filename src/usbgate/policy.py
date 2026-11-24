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


DEMO = "presence-demo.service"
TIMER = "usbgate-reconcile.timer"
WORKER = "usbgate-reconcile.service"
IDENTITY = ("Id", "Names", "LoadState", "FragmentPath", "DropInPaths", "NeedDaemonReload", "Transient")
EXTRA_RELATIONS = ("RequiredBy", "RequisiteOf", "BindsTo", "Requisite", "Upholds", "UpheldBy",
                   "OnSuccess", "OnSuccessOf", "OnFailureOf", "WantedBy", "ConflictedBy", "Requires", "Wants")
ACTIONS = ("SuccessAction", "FailureAction", "StartLimitAction", "JobTimeoutAction")
TMP_MOUNTS = {"-.mount", "tmp.mount", "var.mount", "var-tmp.mount"}


def _expect(data, **expected):
    for field, value in expected.items():
        if data[field] != value:
            raise ValueError(f"{data['Id']}: unexpected {field}={data[field]!r}, expected {value!r}")


def _fixed_identity(data, name):
    _expect(data, Id=name, Names=name, LoadState="loaded", DropInPaths="", Transient="no",
            FragmentPath=f"/etc/systemd/system/{name}", NeedDaemonReload="no")


def _fixed_relationships(data, name):
    # Ordering (Before/After) does not pull another unit into the transaction.
    allowed = {
        "Requires": {"sysinit.target", "system.slice"} | TMP_MOUNTS,
        "Wants": TMP_MOUNTS,
        "Conflicts": {"shutdown.target"}, "ConflictedBy": {"shutdown.target"},
    }
    if name == TIMER:
        allowed.update(Triggers={WORKER}, WantedBy={"timers.target"})
    if name == WORKER:
        allowed.update(TriggeredBy={TIMER})
    for field in (*STOP_RISK, "Conflicts", *EXTRA_RELATIONS):
        unexpected = set(data[field].split()) - allowed.get(field, set())
        if unexpected:
            raise ValueError(f"{name}: unexpected {field}: {' '.join(sorted(unexpected))}")
    required = {"sysinit.target"} if name == TIMER else {"sysinit.target", "system.slice"}
    if not required.issubset(data["Requires"].split()) or "shutdown.target" not in data["Conflicts"].split():
        raise ValueError(f"{name}: missing default system dependencies")
    _expect(data, **dict.fromkeys(ACTIONS, "none"))


def verify_monitor_units(*, operational):
    """Check the fixed timer and worker without requiring the oneshot to be running."""
    fields = IDENTITY + STOP_RISK + ("Conflicts",) + EXTRA_RELATIONS + ACTIONS
    timer = _unit_properties(TIMER, fields + ("Unit", "UnitFileState", "ActiveState", "SubState", "Job"),
                             subprocess.run)
    _fixed_identity(timer, TIMER)
    _fixed_relationships(timer, TIMER)
    _expect(timer, Unit=WORKER, Triggers=WORKER)
    if operational:
        _expect(timer, ActiveState="active", UnitFileState="enabled", Job="")
        if timer["SubState"] not in ("running", "waiting"):
            raise ValueError(f"{TIMER}: unexpected SubState={timer['SubState']!r}")
    worker = _unit_properties(WORKER, fields, subprocess.run)
    _fixed_identity(worker, WORKER)
    _fixed_relationships(worker, WORKER)


def _unit_properties(name, fields, runner):
    cmd = ["/usr/bin/systemctl", "show", "--no-pager", "--all",
           "--property=" + ",".join(fields), name]
    result = runner(cmd, check=False, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError(f"systemctl show {name} exited {result.returncode}: {result.stderr.strip()}")
    data = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition("=")
        if not sep or key not in fields or key in data:
            raise ValueError(f"{name}: malformed systemctl response")
        data[key] = value
    if data.keys() != set(fields):
        raise ValueError(f"{name}: incomplete systemctl response")
    return data


def unit_state(name):
    """Return a confirmed manager state. An unknown result carries its cause."""
    fields = ("Id", "LoadState", "ActiveState", "SubState", "Job")
    try:
        properties = _unit_properties(name, fields, subprocess.run)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"{name}: state unknown: {exc}") from exc
    if properties["Id"] != name or not properties["ActiveState"] or not properties["SubState"]:
        raise RuntimeError(f"{name}: state unknown: empty or mismatched unit properties")
    if properties["LoadState"] != "loaded":
        raise RuntimeError(f"{name}: state unknown: LoadState={properties['LoadState']}")
    job = properties["Job"]
    if job:
        if not re.fullmatch(r"[1-9][0-9]*", job):
            raise RuntimeError(f"{name}: state unknown: malformed Job property")
        return "transitioning"
    active, sub = properties["ActiveState"], properties["SubState"]
    if active == "inactive" and sub == "dead":
        return "inactive"
    active_substates = ("waiting", "running", "elapsed") if name.endswith(".timer") else ("running", "exited")
    if active == "active" and sub in active_substates:
        return "active"
    if active in ("activating", "deactivating", "reloading", "refreshing", "maintenance"):
        return "transitioning"
    if active == "failed" and sub == "failed":
        return "failed"
    raise RuntimeError(f"{name}: state unknown: ActiveState={active}, SubState={sub}")


def validate_name(name):
    if not isinstance(name, str) or not UNIT.fullmatch(name):
        raise ValueError("only plain .service or .socket unit names are accepted")
    base = name.rsplit(".", 1)[0].lower()
    if base in DENY_EXACT or any(base.startswith(p) for p in DENY_PREFIX):
        raise ValueError("protected or potentially critical unit refused")
    return name


def inspect_unit(name, runner=None):
    """Read effective manager metadata, never authorize enforcement."""
    validate_name(name)
    fields = FIELDS
    if name == DEMO:
        fields += ("NeedDaemonReload", "Transient", "CanStart", "Job", "ActiveState", "SubState",
                   "Type", "DynamicUser", "Slice", "RefuseManualStop", "RefuseManualStart") + EXTRA_RELATIONS + ACTIONS
    data = _unit_properties(name, fields, runner or subprocess.run)
    if name == DEMO:
        _fixed_identity(data, DEMO)
        _expect(data, CanStart="yes", Job="", Type="simple", DynamicUser="yes", Slice="system.slice",
                RefuseManualStop="no", RefuseManualStart="no")
        if (data["ActiveState"], data["SubState"]) not in {
            ("inactive", "dead"), ("active", "running"), ("failed", "failed")
        }:
            raise ValueError(f"{name}: unconfirmed service state {data['ActiveState']}/{data['SubState']}")
        _fixed_relationships(data, DEMO)
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
