# usb-presence-gate

A small, lightweight USB presence observer and **opt-in disposable service gate** for headless Debian 13. This project explores physical-presence gating for selected noncritical services. **USB identifiers are clonable and do not authenticate a person.** The first release is observation-only; the next draft adds control of **one project-owned disposable service** only. It does not provide general service enrollment, change SSH or mount USB media.

**Validation (2026-11-22):** 10 initial unit tests passed on the physical Debian 13 notebook. The maintainer also verified USB scanning, installation, timer activation, physical removal, 10-second absence grace, reconnect, journald events, disable and uninstall. The USB event path was verified end-to-end, but **udev-triggered versus timer-triggered reconciliation was not isolated**. See [hardware validation](docs/hardware-validation-2026-11-22.md) for precise evidence and remaining limitations. The expanded offline regression suite is verified by GitHub Actions on the feature branch; changed installation behavior still needs fresh hardware verification.

## Safety before starting

Keep **two independent SSH sessions** connected and the local keyboard/display within reach before enabling observation. No Docker, VM or graphical environment is required. Do not enable the disposable demo gate before its branch has passed CI, review and notebook safety checks.

## Operations

### Install

**Status: hardware-verified on 2026-11-22 (before the follow-up patch); re-test changed installer behavior before merge.** The following commands show the merged observation release. For the demo draft, check out `feature/demo-service-gate` instead and review its warnings before installation.

```sh
git clone https://github.com/kayo-willian/usb-presence-gate.git
cd usb-presence-gate
git switch main
make test
sudo make install
/usr/local/sbin/usbgate --help
```

Installation is inert: it copies files and writes a hash manifest, but does **not** enable any udev rule, timer or service.

### Setup

**Status: hardware-verified on 2026-11-22 (before the follow-up patch).** Observation alone may be enabled:

```sh
sudo /usr/local/sbin/usbgate doctor
sudo /usr/local/sbin/usbgate monitor enable
```

### Scan

**Status: hardware-verified in observation-only mode.** This command lists USB descriptors and redacted fingerprints; it does not register a device:

```sh
/usr/local/sbin/usbgate scan
```

### Enable

**Merged release:** `monitor enable` starts observation only. The disposable demo control described below is **new, untested on hardware and opt-in**.

### Test

**Status: hardware-verified for physical removal, 10-second absence grace and return on 2026-11-22.** With observation enabled, insert and remove a **disposable** USB stick. After removal, leave it unplugged for more than 10 seconds and inspect the state. Do not modify production services.

```sh
/usr/local/sbin/usbgate scan
sudo /usr/local/sbin/usbgate status --json
sudo journalctl -t usbgate -n 40 --no-pager
sudo systemctl status usbgate-reconcile.timer --no-pager
```

Verified behavior: a first removal records `device_absence_pending`, then `device_absent` after a 10-second grace even without another USB event. The first absence time survives restarts **within the same boot**.

### Status

**Status: hardware-verified on 2026-11-22.**

```sh
sudo /usr/local/sbin/usbgate status
sudo /usr/local/sbin/usbgate status --json
sudo /usr/local/sbin/usbgate doctor
```

### Disable

**Status: hardware-verified on 2026-11-22; simulated partial-failure cleanup unit-tested.** This turns off observation, not future policies.

```sh
sudo /usr/local/sbin/usbgate monitor disable
```

### Recover

**Status: observation-only manual recovery; host untested.** If the CLI is unavailable, deactivate the observer using systemd and remove **only** the owned udev rule:

```sh
sudo systemctl disable --now usbgate-reconcile.timer
sudo systemctl stop usbgate-reconcile.service
sudo rm -f /etc/udev/rules.d/70-usbgate.rules
sudo udevadm control --reload
```

This fallback applies only to the observation release. It is **not** a substitute for recovery procedures once actual service enforcement exists.

### Uninstall

**Status: hardware-verified on 2026-11-22 (before the follow-up patch); additional installer safety tests are CI-verified but not hardware-verified.** Disable observation first, then from the same source checkout:

```sh
sudo make uninstall
sudo systemctl daemon-reload
```

The installer refuses overwrites of existing paths. The manifest limits removal to files whose content is unchanged. In the demo draft, disable and reset demo enrollment before uninstall. Runtime observations and empty directories may remain. There is no automatic purge.

### Read-only candidate unit inspection

Before implementing service control, inspect a disposable, locally managed
systemd unit. This is **not enrollment** and does not start or stop anything.
Passing this conservative preflight does not guarantee a safe dependency graph.

```sh
PYTHONPATH=src python3 -m usbgate.cli inspect-unit demo-gate.service
```

The candidate unit must exist in `/etc/systemd/system`. Avoid SSH, network,
firewall, Docker, authentication and other essential units. The gating roadmap
and remaining safety checks are in [completion plan](docs/completion-plan.md).

## Disposable demonstration gate (new draft; untested on hardware)

The new opt-in demo controls only `presence-demo.service`, a project-owned
service that runs an idle `/usr/bin/sleep infinity` process under a
systemd-managed dynamic user (`DynamicUser=yes`).
It never controls SSH, the network, Docker or a user service. Device identifiers
are easily imitated; this is a presence lab, **not authentication**.

This draft must first pass offline tests and inspection. **Do not enable it on
the physical notebook until after review.** Once approved, the planned lab is:

```sh
# On the dedicated Debian notebook, from this feature branch:
make test
sudo make install
sudo systemctl daemon-reload
sudo /usr/local/sbin/usbgate monitor enable
/usr/local/sbin/usbgate scan
sudo /usr/local/sbin/usbgate demo enroll REPLACE_WITH_12_CHARACTER_FINGERPRINT
sudo /usr/local/sbin/usbgate demo enable
sudo /usr/local/sbin/usbgate demo status
sudo systemctl status presence-demo.service --no-pager
```

Physically remove the USB stick, allow 10 seconds of grace, verify the demo
service stops, then reconnect and verify it starts again. Check journald.
Record exactly what happened; these results are **not yet hardware-verified**.

```sh
sudo /usr/local/sbin/usbgate demo disable
sudo /usr/local/sbin/usbgate demo reset
sudo /usr/local/sbin/usbgate monitor disable
sudo make uninstall
sudo systemctl daemon-reload
```

`demo disable` stops only the disposable demo. `monitor disable` refuses to
run while demo control is enabled. Uninstallation refuses remaining enrollment.

### Manual demo recovery without Python or the USB stick

When demo control is enabled, execute from a local console if SSH is impaired.
The commands affect only the **project-owned** demo service and rule:

```sh
sudo systemctl disable --now usbgate-reconcile.timer
sudo systemctl stop usbgate-reconcile.service
sudo rm -f /etc/udev/rules.d/70-usbgate.rules
sudo udevadm control --reload
sudo rm -f /run/usbgate/demo-grant
sudo systemctl stop presence-demo.service
sudo mv /etc/usbgate/demo.json /etc/usbgate/demo.json.disabled
sudo systemctl daemon-reload
```

Keep the policy backup for inspection. If a command fails, investigate before
considering recovery complete. This demo does not claim provable stop latency
under kernel failure, missed events or a broken systemd manager.

## Technical notes

The observer reads USB descriptors from sysfs and stores only short hashes, bus locations and interface classes. When multiple devices report the same VID, PID and serial, the scan marks that fingerprint **ambiguous**, records its device count and bus locations, and cannot distinguish individual removals within that group. An ambiguous or serial-less identifier must never qualify for future enrollment. Fingerprints do not uniquely authenticate physical hardware. Hashes allow correlation but **are not device authentication** and may reveal a short identifier to someone who can guess it. Its volatile state is under `/run/usbgate/`; a short oneshot Python worker is triggered by fixed udev events and a periodic systemd timer. No daemon remains resident. **The safety timer must be active in any future enforcement mode**; it is optional only while observing.

Review [lifecycle](docs/lifecycle.md), [threat model](docs/threat-model.md) and [prior art](docs/prior-art.md) before future enrollment or enforcement work.

## Credits and development

Inspired by **Henrique ([@rique-decoder](https://github.com/rique-decoder))**, whose open-source [Linux USB Security Token](https://github.com/rique-decoder/linux-usb-security-token) explores USB-based login on Linux desktops. The headless observation architecture here is independent; no upstream code was copied. [USBGuard](https://github.com/USBGuard/usbguard) is a separate tool for USB device authorization.

AI tools assisted with architecture review, code and documentation. The maintainer sets requirements, reviews changes and supplies real notebook test evidence.
