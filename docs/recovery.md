# Recovery, diagnostics and removal

This page documents the **project-owned disposable demo**, not system recovery
for arbitrary Linux services. The original procedure was manually tested on the
physical Debian 13 notebook on 2026-11-22. The revised ordering and
current hardening still require live validation.

The demo is not a cryptographic authentication mechanism. Recovery must never
require the USB drive or a working Python interpreter. Keep at least one
independent console access path before using it on a remote headless host.

## A. Check the state without changing it

If the installed launcher works:

```sh
sudo /usr/local/sbin/usbgate doctor
sudo /usr/local/sbin/usbgate status --json
sudo /usr/local/sbin/usbgate demo status
```

Regardless of the CLI:

```sh
sudo systemctl is-active usbgate-reconcile.timer
sudo systemctl is-active usbgate-reconcile.service
sudo systemctl is-active presence-demo.service
sudo journalctl -u usbgate-reconcile.service -n 60 --no-pager
sudo journalctl -t usbgate -n 60 --no-pager
```

`is-active` normally returns a nonzero exit code when a unit is inactive.
The project normally touches no other system services.

## B. Normal shutdown (Python and CLI are available)

If the demo is enrolled (armed or disarmed):

```sh
sudo /usr/local/sbin/usbgate demo disable
sudo /usr/local/sbin/usbgate demo reset
sudo /usr/local/sbin/usbgate monitor disable
```

If the demo was never enrolled, skip `demo disable` and `demo reset`.
If monitoring was never enabled, `monitor disable` is optional.

From the same project source checkout used to install:

```sh
sudo make uninstall
sudo systemctl daemon-reload
```

Do not bypass an uninstall refusal by forcibly removing arbitrary files.
The live installer checks the manifest and requires confirmed inactivity for
the timer, worker and demo before deleting files. A missing unit, pending job,
failed state or unreadable manager response leaves the installed files in place.
Inspect the manager or restore the expected unit definitions before retrying.

### Interrupted administrative commands

Check `sudo /usr/local/sbin/usbgate demo status` for policy, grant, service
state and `authorization_inhibited`. The marker lives at
`/var/lib/usbgate/authorization-inhibited`. It survives process exit and a
normal reboot. A worker that sees it attempts verified closure. The locks in
`/run` are automatically released on process exit.

After correcting the reported filesystem or manager failure, retry
`demo disable` for an enrolled policy, then retry `monitor disable` or
`monitor enable` according to the desired monitoring state. These commands
work without the USB. A successful monitor transition clears a stale marker
only after checking its result. An armed policy with a stale marker must be
disarmed first. Preserve the marker during Python-independent recovery below.
It can remain after manual uninstall and will inhibit a later installation
until monitoring is configured successfully.

If the disabled policy and the independent marker both fail to persist, an
armed policy can authorize a later start. Inspect the reported closure outcome
and use manual recovery if necessary. A failed stop can leave a process active
even when future authorization is blocked. Sudden power loss, external root
changes, and manager failure have no demonstrated recovery deadline.

## C. Manual recovery without Python

The procedure below assumes the original project units and relationships.
If the worker reports `unsafe to stop`, or any project unit or rule differs
from its installed configuration, first inspect the effective fragments,
drop-ins, relationships and rule. A manual stop of a modified unit can
propagate to another service. Resolve the discrepancy before acting; preserve
administrator-modified rules and evidence. If grant removal failed, also inspect the grant path: an inactive
service can still be eligible for a later start.

```sh
sudo systemctl disable --now usbgate-reconcile.timer
sudo rm -f /etc/udev/rules.d/70-usbgate.rules
sudo udevadm control --reload
sudo systemctl stop usbgate-reconcile.service
```

Remove only the verified project-owned rule. Confirm the worker is inactive
before proceeding. Preserve any existing administrative inhibit marker.

```sh
sudo rm -f /run/usbgate/demo-grant
sudo systemctl stop presence-demo.service
sudo mv -n /etc/usbgate/demo.json /etc/usbgate/demo.json.disabled
sudo systemctl daemon-reload
```

The `mv` line assumes a live `demo.json` exists and the destination
`demo.json.disabled` does **not** already exist. If the policy is missing
or an existing backup is present, **inspect it first and choose a unique
backup name**; do not overwrite existing operator data. Keep the saved
policy for investigation.

If a systemctl command fails, do not assume closure is complete. Inspect
`systemctl status` and `journalctl`, retain the evidence, and use local
console recovery if necessary. The system cannot guarantee closure when
the underlying system manager or kernel is unavailable.

Verify without relying on Python:

```sh
sudo systemctl is-enabled usbgate-reconcile.timer
sudo systemctl is-active presence-demo.service
sudo systemctl is-active usbgate-reconcile.timer
sudo systemctl is-active usbgate-reconcile.service
sudo test ! -e /run/usbgate/demo-grant && echo "Demo grant absent"
sudo test ! -e /etc/usbgate/demo.json && echo "Active demo policy absent"
```

The timer should report `disabled`, all three unit activity checks should
report `inactive`, and the two file checks should report the absence of a
grant and live policy.

After checking, it is possible to run `sudo make uninstall` from the
same source checkout. The **backup policy is intentionally preserved**
and is not in the manifest.

## D. Inert install / update and file-integrity failures

- `make install` refuses occupied targets, symlink parents and an existing
  install manifest. Inspect file ownership first; **do not overwrite**.
- `make uninstall` compares hashes of managed installed files against
  `/var/lib/usbgate/install-manifest.json`. If an installed file changed,
  it refuses removal. Keep evidence before repairing; do not casually
  delete the manifest.
- The checkout's source code must correspond to the installed version
  when using `sudo make uninstall`. Reinstall is not an in-place upgrade:
  normal disable/reset/uninstall must come first.
- `systemctl daemon-reload` is required after installing or removing unit
  files. Unit files installed from source are inert until explicit activation.
- No forced cleanup script is provided because deleting arbitrary files from
  `/etc/systemd/system` or `/etc/udev/rules.d` is dangerous.

## E. Residual data and optional repository removal

The source checkout is different from the installed application. The
manifest deliberately does **not** include operator policy backups,
volatile observation state, logs, or unrelated data.

After fully uninstalling and verifying the project services are inactive,
you may inspect the known leftovers:

```sh
sudo ls -la /etc/usbgate /var/lib/usbgate /run/usbgate
```

Missing directories will produce a harmless error. Review each item
before removal; the manual recovery backup is typically
`/etc/usbgate/demo.json.disabled`. Never delete a directory just because
it looks similar to a project path.

Only after confirming the project is backed up on GitHub and your local
working tree has no unsaved work, optionally remove the local clone:

```sh
cd ~
rm -rf -- "$HOME/usb-presence-gate"
```

This permanently deletes the **local working copy**, not the remote
GitHub repository.

[Português (Brasil)](../pt-BR/docs/recuperacao.md) · [Project overview](../README.md)
