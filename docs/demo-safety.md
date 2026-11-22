# Disposable gate safety boundary

This draft adds a deliberately restricted **demonstration**, not generic
service/socket enforcement. The controlled unit is hardcoded to
`presence-demo.service`, installed as a root-owned project file with
`ConditionPathExists=/run/usbgate/demo-grant`. The process runs under a transient systemd-managed identity
(`DynamicUser=yes`) and does no networking or application work.
This replaced the original `User=nobody` configuration after the maintainer's
Debian 13 `systemd-analyze verify` output warned that the shared nobody
account is unsafe for this purpose. The maintainer subsequently reran `systemd-analyze verify` on the target
Debian 13 notebook after this change; it completed without warnings.

The demo enrollment accepts only one currently connected USB storage device
with a non-empty, unambiguous serial-based descriptor fingerprint. Descriptor
cloning, stolen devices and malicious physical devices are **not** prevented.
No raw serial is stored; the fingerprint itself is linkable.

Enable requires a verified installed unit, an enabled active safety timer and
the observed USB descriptor. Only an explicitly enabled demo policy permits
grant creation. A missing/corrupt policy, timer failure or descriptor mismatch
causes the worker to remove the volatile grant and try to stop the demo.
Removal first enters a persisted 10-second grace; it closes after the
observed absence timer expires. A quick return cancels that absence.

A scheduled worker is **not** a hard security boundary. Systemd can fail,
udev can miss events, process termination can be delayed, and the Python
worker can crash. The condition on the unit prevents ordinary manual starts
when the grant is absent, but removing the grant alone cannot stop an
already-running service. The worker explicitly requests a stop and checks it.

Manual recovery does not require Python or USB and is documented in README.
No source files, unit IDs or subprocess arguments come from the USB.
Only `presence-demo.service` is started or stopped; SSH, network,
firewalls, PAM, Docker and other services remain untouched.

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

This is **evidence of the basic happy path**, not proof of full security.
No raw serial, actual fingerprint or hostname is published here. The
exact stop latency, whether udev or the timer performed each transition,
quick reconnect before grace expiry, timer loss, corrupt-policy recovery,
complete source-based uninstall and post-uninstall cleanup remain unverified.

## Validation still needed on the real notebook

1. Run new unit/CI tests.
2. Verify inert install and a clean, refused unconfigured demo.
3. Verify explicit enrollment/enable of the disposable unit only.
4. Verify physical unplug with grace, reconnection and repeated worker cycles.
5. Confirm manual start while grant absent cannot run the demo.
6. Verify fail-closed behavior on timer loss and invalid applied policy.
7. Verify CLI reset and source-based uninstall, including leftover policy backups.
8. Measure systemd timer/udev path separately; update published evidence.

These are tests to perform, **not claims of having performed them**.
