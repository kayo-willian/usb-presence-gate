# Disposable gate safety boundary

The completed experimental milestone includes a deliberately restricted
**demonstration**, not generic service/socket enforcement. The controlled unit is hardcoded to
`presence-demo.service`, installed as a root-owned project file with
`ConditionPathExists=/run/usbgate/demo-grant`. The process runs under
a transient systemd-managed identity (`DynamicUser=yes`) and does no
networking or application work.
This replaced the original `User=nobody` configuration after the
maintainer's Debian 13 `systemd-analyze verify` check warned that the
shared nobody account was unsafe. The updated unit passed a new static
verification on that notebook with no warnings.

The demo enrollment accepts only one currently connected USB storage device
with a non-empty, unambiguous serial-based descriptor fingerprint. Descriptor
cloning, stolen devices and malicious physical devices are **not** prevented.
No raw serial is stored; the fingerprint itself is linkable.

Enable checks the installed unit, active timer and current USB descriptor.
The worker and initial enable commit the observation before granting access.
Physical absence has a ten-second grace period measured from detection.
An observation write failure skips that grace and attempts closure immediately.
The command reports the write error even when closure succeeds.

The closure result accounts for both the authorization file and the running service.

- Grant removal is attempted even when the unit fails its safety check.
  An unlink error or a refused symlink is reported alongside the service outcome.
  A remaining grant can still satisfy the unit's start condition.
- The worker queries the actual service even with a missing or disabled policy
  and no grant. If shutdown is needed, it verifies the installed file against
  the manifest and checks effective systemd properties before issuing a stop.
  A failed safety check blocks the stop request and requires operator review.
  After a stop request, the worker queries the manager again, including when
  the request timed out. A confirmed stop requires the canonical, loaded unit
  to report `inactive/dead` with an empty `Job` property.

`demo status` reports `service_state` as `active`, `inactive`, `transitioning`,
`failed`, or `unknown`. The compatibility field `service_active` is JSON
`null` for the last three. An unknown result includes a diagnostic.
These observations describe the instant of the manager query. Later jobs,
a stalled worker, or an unreachable manager can still require [manual recovery](recovery.md).

Offline regression tests use temporary files and simulated systemd replies,
including interrupted communication and simultaneous persistence, revocation
and stop failures. The physical observations below predate these changes.
Updated failure paths and timing on the Debian notebook await hardware validation.
Manual recovery works independently of Python and USB. The only demo actuator
target is `presence-demo.service`. USB fields supply neither unit names nor
subprocess arguments.

## Physical notebook observations — 2026-11-22

The maintainer reported the following outputs from the Debian 13 notebook
on this draft branch:

- The full **41-test suite passed**; `systemd-analyze verify` completed
  without output after the dynamic-user change.
- `sudo make install` installed inert files, and `demo status`
  initially reported `state=unconfigured`, no grant and an inactive demo.
- The read-only `inspect-unit presence-demo.service` preflight passed.
- Explicit `monitor enable` reported observation only. An explicitly
  enrolled USB storage fingerprint remained disabled until `demo enable`.
- With the USB stick connected, `demo enable` reported success and
  `demo status` reported enabled, grant present, service active;
  systemd separately reported `active`.
- After physical removal, `demo status` reported grant absent and service
  inactive; the observer recorded the device `absent` and the safety
  timer `active`.
- After physical reconnection, `demo status` again reported the grant
  and service active, with systemd independently reporting `active`.
- With the demo disabled, the maintainer tried to start
  `presence-demo.service` manually; the service remained inactive and
  the grant absent (`state=enrolled`).
- Explicit re-enable restored both the grant and the running service.
- After reboot with the stick connected, SSH returned, the safety
  timer was active, and both grant and disposable service were active.
- A Python-independent manual recovery was executed successfully:
  the timer and worker were stopped, the project-owned udev rule
  removed and reloaded, the demo grant revoked, the demo service
  stopped, and the saved policy moved aside. Subsequent CLI checks
  reported `state=unconfigured`, no grant, service inactive and
  timer inactive.

- After manual recovery, the maintainer ran `sudo make uninstall` followed
  by `systemctl daemon-reload`; manifest-owned files were removed and a
  subsequent shell test confirmed `/usr/local/sbin/usbgate` absent. The
  backup `/etc/usbgate/demo.json.disabled` was intentionally retained.

These are **hardware observations, not proof of authentication or a hard
security boundary**.
No raw serial, actual fingerprint or hostname is published here. The
exact stop latency, whether udev or the timer initiated each transition,
quick reconnect before grace expiry, timer loss and corrupt-policy recovery
remain unverified. Backup deletion is deliberately a separate operator
choice, not part of the manifest-based uninstall.

## Tests not yet established on the physical host

These limitations remain even though the demonstration's core lifecycle
was physically observed:

- Quick USB reconnection **inside** the grace interval.
- A missed udev event with proven timer-only fallback.
- Corrupted policy, deleted timer, repeated manager failure, forced crash
  and hostile cloned-descriptor behavior on the physical notebook.
- A guaranteed maximum time between physical removal and process stop.
- A CLI `demo reset` after a normal `demo disable` (unit-tested only).
- Deployment to or protection of any real existing application, or
  multiple units/sockets (not implemented).

The backup created by manual recovery is deliberately retained until
the administrator separately inspects and deletes it. The documented
physical source-based uninstall did not claim to purge that backup.
Physical acceptance evidence is not a security certification.
