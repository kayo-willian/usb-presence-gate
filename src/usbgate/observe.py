"""Pure presence transitions; no policy enforcement."""

def advance(previous, present, now, boot_id, grace=10):
    if not 0 <= grace <= 120:
        raise ValueError("grace out of range")
    old = previous.get("devices", {}) if previous.get("boot_id") == boot_id else {}
    new, events, wait = {}, [], None
    for key in sorted(set(old) | set(present)):
        before = old.get(key, {})
        state = before.get("state")
        if key in present:
            new[key] = {"state": "present", "absent_since": None}
            if state != "present":
                events.append(("device_present" if state is None else "device_returned", key))
        elif state == "absent":
            new[key] = before
        elif state in ("present", "pending"):
            since = before.get("absent_since")
            if not isinstance(since, (int, float)) or since < 0 or since > now:
                since = now
            remaining = max(0, grace - (now - since))
            new[key] = {"state": "pending" if remaining else "absent", "absent_since": since}
            if remaining:
                if state != "pending":
                    events.append(("device_absence_pending", key))
                wait = min(wait, remaining) if wait is not None else remaining
            else:
                events.append(("device_absent", key))
    return {"schema_version": 1, "boot_id": boot_id, "devices": new}, events, wait
