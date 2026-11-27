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

## Effective units, timer and udev

Authorization trusts the root-owned installation manifest under `/var/lib/usbgate`.
The demo, timer, worker and reference udev rule must match their installed
SHA-256 hashes. The deployed udev rule must have identical bytes to the
verified reference. Each checked file must be regular, root-owned and free
of group or other write access. The same ownership and write restrictions
apply to parent directories, and symbolic links in these paths are refused.
A local installation with a group-writable prefix will need administrator
review. The project never repairs permissions or overwrites a modified rule.

The manager must report the single expected name and canonical fragment
under `/etc/systemd/system/` for each unit, with no drop-ins, transient
definition or pending daemon reload. Both starting and stopping the demo
require the expected simple service type, dynamic user, system slice,
manual control eligibility and safe relationships. A new start also requires
`inactive/dead` with an empty `Job`. When a job is pending or the service
is transitioning, the gate revokes the grant and can request a stop after
rechecking the unit. With systemd's default job mode, a stop can replace a
conflicting queued start. Closure still requires a fresh observation of
`inactive/dead` with no job. [Debian systemctl(1)](https://manpages.debian.org/trixie/systemd/systemctl.1.en.html)

The fixed-unit checks examine direct transaction relationships. They allow
`Requires=` on the normal system slice and sysinit target, and mount
dependencies for the root, `/tmp`, `/var` and `/var/tmp` paths used by
private temporary directories. They allow the shutdown-target conflict and
the shipped timer/worker trigger pair and timer installation under
`timers.target`. Unexpected pull-ins, reverse requirements, stop propagation,
upholding, success/failure activators, conflicts and emergency actions
cause refusal. Pure ordering through `Before=` or `After=` does not pull
a unit into a transaction. The generic read-only candidate inspection retains
its narrower purpose. [Debian systemd.unit(5)](https://manpages.debian.org/trixie/systemd/systemd.unit.5.en.html)

The periodic timer must report `active` and `waiting` or `running`, an empty
job, `UnitFileState=enabled` and the expected worker in both `Unit` and
`Triggers`. The persistent symlink under `/etc/systemd/system/timers.target.wants/`
must resolve to the verified timer fragment. An elapsed or runtime-enabled
timer cannot authorize the demo. The oneshot worker may be inactive between
runs. During initial monitor setup, file and effective configuration checks
precede activation and persistent enablement is verified afterward.
`monitor disable` clears the administrative inhibit only after confirming
the timer is `inactive/dead` with an empty job, `UnitFileState=disabled`,
and no remaining `WantedBy` relationship. The boot link must be absent
(a dangling symlink still counts as present) and the observer must report
`inactive/dead` with no job. An inconclusive check leaves the inhibit in place.
[Debian systemd.timer(5)](https://manpages.debian.org/trixie/systemd/systemd.timer.5.en.html)

`doctor` and `status --json` expose `monitor_safety` as `verified` or a
diagnostic; use sudo to read the installation manifest. `timer_active`
continues to describe current activity alone. A monitoring failure blocks
authorization and triggers verified closure on reconciliation. A failed
structural check prevents the worker from stopping an active demo.
Review the named fragment, relationship, rule, permissions or enablement
before retrying recovery. A failed monitor transition retains its inhibit.

These checks sample disk and manager state. They trust the installation
source, root administrator and manager; they do not traverse the full
transitive dependency graph or serialize external privileged changes.
Matching rule bytes cannot confirm delivery by udev. Offline tests cover
refusal and recovery with simulated manager replies. Effective properties
on the physical notebook, event delivery and timer-only wakeups after boot
still need live validation.

## Administrative transitions

All mutating monitor and demo commands take `/run/usbgate/admin.lock` first.
They take the observer lock when reading or changing authorization. The worker
only takes the observer lock. A monitor command records a persistent inhibit
marker and closes the demo under that lock, then releases the observer lock
before asking systemd to start or stop the worker. A worker can finish during
that wait and can only close the demo while the marker exists. The monitor
clears the marker after the commands and final state checks succeed.

Initial enable commits the USB observation and checks the fixed unit and
manager before opening the grant. The policy remains disabled until the
service is confirmed active and the monitor is checked again. A worker after
an interruption before the policy commit closes any leftover grant or demo.
After the commit, activation stands even if the CLI was killed before printing
success. A reported activation failure attempts disarm, revocation and safe
shutdown and reports their outcomes.

Once armed, the demo follows the observed USB state. A fresh, eligible sample
and a confirmed inactive service cause a start even if the grant already
exists. This recovers interrupted worker starts and also reverses a manual
service stop while the USB remains eligible. Use `demo disable` to keep it
stopped. Failed, transitioning and unknown states cannot authorize a start.

Disable records the inhibit marker and writes the disabled policy before
closure. An incomplete operation can therefore leave a disabled policy with
a process still running. Status exposes `authorization_inhibited` independently
of policy and service state. See [administrative recovery](recovery.md#interrupted-administrative-commands).

The concurrency tests use separate Linux processes, real file locks and
synchronization barriers. Service responses and USB observations are simulated.
Live Debian manager timing and reboot during a transition await validation.

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

[Português (Brasil)](../pt-BR/docs/demo-safety.md) · [Project overview](../README.md)
