# usb-presence-gate

A small, lightweight **USB presence observer** for headless Debian 13. This project explores physical-presence gating for selected noncritical services. **USB identifiers are clonable and do not authenticate a person.** The current base PR is **observation-only**: it never controls services, creates policy gates, changes SSH, or mounts USB media.

**Validation:** unit-tested in a simulated offline environment; the new observer, udev event delivery, timer and live installation are **untested** on the target Debian notebook. [Previously verified notebook prerequisites](docs/hypotheses.md) include Python 3.13.5, tomllib and CLOCK_BOOTTIME.

## Safety before starting

Keep **two independent SSH sessions** connected and the local keyboard/display within reach before enabling observation. No Docker, VM or graphical environment is required. No service or socket should be enrolled in this phase.

## Operations

### Install

**Status: implemented; temporary-root installation unit-tested; live host untested.** These commands must be run from the root of a checkout of the feature branch until this PR is merged.

```sh
git clone https://github.com/kayo-willian/usb-presence-gate.git
cd usb-presence-gate
git switch feature/observe-base
make test
sudo make install
/usr/local/sbin/usbgate --help
```

Installation is inert: it copies files and writes a hash manifest, but does **not** enable any udev rule, timer or service.

### Setup

**Status: implemented; hardware untested.** Observation alone may be enabled:

```sh
sudo /usr/local/sbin/usbgate doctor
sudo /usr/local/sbin/usbgate monitor enable
```

### Enroll

**Status: not implemented.** The following command only lists USB descriptors and redacted fingerprints; it does not register a device:

```sh
/usr/local/sbin/usbgate scan
```

### Enable

**Status: enforcement not implemented.** `monitor enable` starts observation only. No service availability policy is installed.

### Test

**Status: simulated unit tests passed; target USB behavior untested.** With observation enabled, insert and remove a **disposable** USB stick. After removal, leave it unplugged for more than 10 seconds and inspect the state. Do not modify production services.

```sh
/usr/local/sbin/usbgate scan
sudo /usr/local/sbin/usbgate status --json
sudo journalctl -t usbgate -n 40 --no-pager
sudo systemctl status usbgate-reconcile.timer --no-pager
```

Expected behavior (not yet hardware-verified): a first removal records `device_absence_pending`, then `device_absent` after a 10-second grace even without another USB event. The first absence time survives restarts **within the same boot**.

### Status

**Status: implemented; host behavior untested.**

```sh
sudo /usr/local/sbin/usbgate status
sudo /usr/local/sbin/usbgate status --json
sudo /usr/local/sbin/usbgate doctor
```

### Disable

**Status: implemented; partial-failure cleanup unit-tested, host untested.** This turns off observation, not future policies.

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

**Status: temporary-root unit-tested; live host untested.** Disable observation first, then from the same source checkout:

```sh
sudo make uninstall
sudo systemctl daemon-reload
```

The installer refuses overwrites of existing paths. The manifest limits removal to files whose content is unchanged. Runtime observations and empty directories may remain. There is no automatic purge.

## Technical notes

The observer reads USB descriptors from sysfs and stores only short hashes, bus locations and interface classes. Hashes allow correlation but **are not device authentication** and may reveal a short identifier to someone who can guess it. Its volatile state is under `/run/usbgate/`; a short oneshot Python worker is triggered by fixed udev events and a periodic systemd timer. No daemon remains resident. **The safety timer must be active in any future enforcement mode**; it is optional only while observing.

Review [lifecycle](docs/lifecycle.md), [threat model](docs/threat-model.md) and [prior art](docs/prior-art.md) before future enrollment or enforcement work.

## Credits and development

Inspired by **Henrique ([@rique-decoder](https://github.com/rique-decoder))**, whose open-source [Linux USB Security Token](https://github.com/rique-decoder/linux-usb-security-token) explores USB-based login on Linux desktops. The headless observation architecture here is independent; no upstream code was copied. [USBGuard](https://github.com/USBGuard/usbguard) is a separate tool for USB device authorization.

AI tools assisted with architecture review, code and documentation. The maintainer sets requirements, reviews changes and supplies real notebook test evidence.
