# USB Presence Gate

[![Tests](https://github.com/kayo-willian/usb-presence-gate/actions/workflows/test.yml/badge.svg)](https://github.com/kayo-willian/usb-presence-gate/actions/workflows/test.yml)
![Debian 13](https://img.shields.io/badge/Debian-13%20Trixie-A81D33?logo=debian&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2563EB)
![Project status](https://img.shields.io/badge/Status-experimental%20milestone%20complete-64748B)

A minimal, standard-library Python **USB presence observer and opt-in disposable service gate** for a headless Debian 13 Linux host. I built it to understand how physical USB events, systemd, recovery, and service availability interact on a resource-limited machine.

**Project status: experimental milestone completed on November 22, 2026. Active development is paused.** The tested demonstration is complete for its deliberately limited scope, and future expansion remains possible; no new features or maintenance schedule are promised.

> **Read this first:** This is a **presence experiment, not an authentication system or a security product**. USB descriptors can be copied or spoofed. The software controls **only the bundled `presence-demo.service`**, an idle disposable process. It **does not enroll arbitrary existing systemd services or sockets**. Never use it to gate SSH, networking, authentication, a firewall, the Docker engine, or any essential service.

## Contents

- [What it does](#what-it-does)
- [Does the USB stick need a key or file?](#does-the-usb-stick-need-a-key-or-file)
- [Requirements](#requirements)
- [Complete setup and first test](#complete-setup-and-first-test)
- [Everyday commands](#everyday-commands)
- [Stopping, resetting and uninstalling](#stopping-resetting-and-uninstalling)
- [Emergency recovery without Python](#emergency-recovery-without-python)
- [Can I protect my own services?](#can-i-protect-my-own-services)
- [Troubleshooting](#troubleshooting)
- [Limitations and future possibilities](#limitations-and-future-possibilities)
- [Evidence, documentation and credits](#evidence-documentation-and-credits)

## What it does

The observer reads USB **descriptors from sysfs**, rather than opening or mounting a drive. It calculates a shortened SHA-256 fingerprint from the reported vendor ID, product ID, and serial number. Scanning reports whether each fingerprint is `identifier-only`, `weak` (no usable serial), or `ambiguous` (multiple devices reporting the same identity).

The observer runs when the fixed udev rule receives USB add/remove events, with a systemd timer as a periodic fallback. It records presence transitions in volatile state under `/run/usbgate/`. A missing device enters a **10-second grace period after the absence has been detected**. The separately opted-in demo gate can then revoke its grant and stop the demo service. Reconnecting a suitable device can restore the demo.

```text
USB stick (descriptors only; no filesystem access)
             |
      Linux USB sysfs
             |
    udev events + systemd timer
             |
   usbgate-reconcile.service
             |
    observation /run/usbgate/
             |
    optional demo policy in /etc/usbgate/
             |
    temporary grant /run/usbgate/demo-grant
             |
      presence-demo.service
      (disposable sleep process)
```

Installation is **inert**: it copies manifest-owned files and creates the demo unit, but does **not** activate monitoring, enroll the USB stick, start the demo, or modify unrelated services. Observation is opt-in; the demo gate requires a **second explicit opt-in**.

**Important state distinction:** `demo status` may show `state: enabled` while the service is `inactive`. That means the policy is armed, **not** that the USB is present or that the service is running.

## Does the USB stick need a key or file?

**No.** A regular, empty USB flash drive can be used for this demonstration. No special partition, secret file, filesystem format, mount point, or modification to its contents is needed. The project intentionally does **not** read, mount, write, format, or encrypt the drive.

The reported serial number is **not a cryptographic secret**, and the fingerprint is **not proof that the original physical stick is present**. An ordinary text file on the stick would be copyable too. Genuine cryptographic challenge/response would require a different design and appropriate hardware-backed credentials; it is not implemented here.

Only a connected USB mass-storage device with interface class `08` and an unambiguous, non-empty reported serial can be enrolled in the demo. Devices without a usable serial or with duplicate descriptors are refused.

## Requirements

| Component | Required |
| --- | --- |
| Host | Debian 13 (Trixie), headless or with a desktop |
| Service manager | systemd; project tested with systemd 257 |
| Runtime | Python 3.13, standard library only |
| Development tools | Git and Make |
| USB device | Ordinary USB storage stick reporting a usable serial and class `08` |
| Administration | Working `sudo` and **two SSH sessions plus local console access** for live experiments |
| Not required | GUI, Docker, containers, VM, USB mount, internet after download |

These commands install only the development prerequisites, if missing:

```sh
sudo apt update
sudo apt install -y python3 git make
```

**Safety:** Run this only on a test host with a disposable workload. Keep a second SSH session open and make sure you can physically reach the machine. The demo does not intentionally control SSH or the network; physical access is still prudent when testing root-operated system services.

## Complete setup and first test

The workflow below describes the **tested disposable demo**, not a general-purpose service enrollment API. Read through the [recovery section](#emergency-recovery-without-python) before enabling anything.

### 1. Download and check the project

After the PR containing the demo has been merged:

```sh
git clone https://github.com/kayo-willian/usb-presence-gate.git
cd usb-presence-gate
git switch main
make test
systemd-analyze verify packaging/systemd/presence-demo.service
```

Until that PR is merged, its review branch is `feature/demo-service-gate`. Only reviewers who intentionally want the **unmerged code** should check out that branch. The examples in this README describe the milestone after merge; until then,
only the draft PR branch includes the demo features.

Expected: all Python tests pass, and `systemd-analyze verify` reports no warnings for the demo unit. Use `./bin/usbgate --help` to run the development launcher from the checkout. The installed launcher uses Debian’s `/usr/bin/python3` in isolation and loads the package under `/usr/local/lib/usbgate`. Its installation directories must be controlled by trusted administrators.

### 2. Install without activating anything

From the repository directory:

```sh
sudo make install
sudo systemctl daemon-reload
sudo /usr/local/sbin/usbgate doctor
sudo /usr/local/sbin/usbgate demo status
/usr/local/sbin/usbgate inspect-unit presence-demo.service
```

Expected: the installation says `Installed inert files; observation is not enabled.`, the demo is `unconfigured` and `inactive`, and the **read-only preflight** says `preflight: passed`. The preflight is not a guarantee that arbitrary units are safe to control.

### 3. Insert the USB stick and find its fingerprint

Plug your test stick into the Debian host. You may use an **empty** stick.

```sh
/usr/local/sbin/usbgate scan
```

Find the entry for your stick; check `vid_pid`, `classes` and `assurance`. Use **only** an entry showing `"assurance": "identifier-only"` and `"08"` in `classes`. The JSON object key is its **12-character lowercase hexadecimal fingerprint**. Do not paste real serials, fingerprints or host information into public issues.

The scan can show other internal USB peripherals. Choose the correct storage device manually; the project does not automatically guess which device is your key.

### 4. Enable observation (still no service control)

```sh
sudo /usr/local/sbin/usbgate monitor enable
sudo /usr/local/sbin/usbgate status --json
sudo systemctl is-active usbgate-reconcile.timer
```

Expected on a fresh install: `Observation enabled.`, an `active` timer, and an inactive demo. An observer finding a running demo without an enabled policy attempts verified closure.

### 5. Enroll the selected stick, then explicitly arm the demo

First, paste **your own** 12-character fingerprint when prompted:

```sh
printf "Paste the 12-character fingerprint shown by scan: "
read -r FINGERPRINT
sudo /usr/local/sbin/usbgate demo enroll "$FINGERPRINT"
sudo /usr/local/sbin/usbgate demo status
```

Expected: `Demo identity enrolled; enforcement still disabled.` and `state: enrolled`. **Nothing has been started yet.**

Keep the USB stick connected, then explicitly arm the disposable gate:

```sh
sudo /usr/local/sbin/usbgate demo enable
sudo /usr/local/sbin/usbgate demo status
sudo systemctl is-active presence-demo.service
```

Expected with the stick present: `state: enabled`, `grant_file: true`, `service_active: true` and systemd `active`. Only `presence-demo.service` is controlled.

### 6. Physically unplug, observe the stop, then reconnect

Remove the USB stick. **Do not remove the host's internal storage or USB network adapter.** Wait roughly 20 seconds for the usual udev-delivered event and grace period, then check:

```sh
sudo /usr/local/sbin/usbgate demo status
sudo systemctl is-active presence-demo.service
sudo /usr/local/sbin/usbgate status --json
sudo journalctl -t usbgate -n 40 --no-pager
```

Expected once removal has been processed: `grant_file: false`, `service_active: false`, systemd `inactive`, and the selected fingerprint `absent`. **An inactive status may return a nonzero exit code; that is normal.**

**The 10-second grace is not a guaranteed maximum stop latency.** It starts after a successful absence detection. If an event is missed, the periodic timer can discover removal later (nominally about one minute between scans, plus scheduling delays). If the worker or systemd fails, no finite stop deadline is guaranteed. Do not treat 20 seconds as a security promise.

Reconnect the same stick and inspect again:

```sh
sudo /usr/local/sbin/usbgate demo status
sudo systemctl is-active presence-demo.service
```

Expected after the USB event has been processed: grant and demo active again. This removal/reconnect flow was observed on the physical test notebook.

### 7. Optional boot recovery check

With the demo enabled, the stick inserted and physical recovery access available, reboot the **test machine**:

```sh
sudo reboot
```

Reconnect to SSH after the host restarts. Give the systemd boot timer time to run, then check:

```sh
sudo /usr/local/sbin/usbgate demo status
sudo systemctl is-active usbgate-reconcile.timer
sudo systemctl is-active presence-demo.service
```

This was tested on the physical Debian 13 notebook with the USB stick **connected at boot**. Unplugged boot and rapid reconnection within the grace window are separate unverified hardware cases.

## Everyday commands

| Action | Command |
| --- | --- |
| Scan without opening the USB filesystem | `/usr/local/sbin/usbgate scan` |
| Check prerequisites and installation | `sudo /usr/local/sbin/usbgate doctor` |
| Read observer + demo state | `sudo /usr/local/sbin/usbgate status --json` |
| Check demo only | `sudo /usr/local/sbin/usbgate demo status` |
| Read-only check of a candidate unit | `/usr/local/sbin/usbgate inspect-unit presence-demo.service` |
| See USB observation events | `sudo journalctl -t usbgate -n 40 --no-pager` |
| Inspect the timer | `sudo systemctl status usbgate-reconcile.timer --no-pager` |
| Check the disposable unit | `sudo systemctl status presence-demo.service --no-pager` |

Do not start, stop or modify protected system services to troubleshoot this experiment.

## Stopping, resetting and uninstalling

### Normal shutdown and uninstallation

Run these commands **in order**, from the same source checkout used for the installation:

```sh
sudo /usr/local/sbin/usbgate demo disable
sudo /usr/local/sbin/usbgate demo reset
sudo /usr/local/sbin/usbgate monitor disable
sudo make uninstall
sudo systemctl daemon-reload
test ! -e /usr/local/sbin/usbgate && echo "USB Presence Gate removed"
```

`demo disable` stops the disposable service; `demo reset` deletes its enrolled policy; `monitor disable` stops the observer/timer and removes its project-owned udev rule. The installer refuses uninstallation while an active policy or an owned systemd unit is running. **Do not force-remove managed files to bypass a refusal.**

This normal shutdown sequence is supported by the implementation and offline tests. The physical host also verified manifest-based uninstall **after manual recovery**, as described below.

### Removing the Git checkout afterwards (optional)

The installed application and the source checkout are **different things**. Uninstalling leaves the Git repository in your home directory. After confirming the desired commits exist on GitHub and there is nothing unsaved in the checkout:

```sh
cd ~
rm -rf -- "$HOME/usb-presence-gate"
```

This permanently deletes the **local repository copy**, including uncommitted changes. It does not delete the GitHub repository. Do this only when you are finished with the local checkout.

### Leftover runtime data and policy backups

The installer removes only the files recorded in its hash manifest, not backups or operator data. In particular:

- `/etc/usbgate/demo.json.disabled` can remain **if manual recovery renamed the policy**.
- `/run/usbgate/observe.json` and `/run/usbgate/lock` may remain until reboot or manual inspection.
- Empty project directories may remain.

For a previously verified, fully uninstalled instance only, inspect any leftovers and delete **only known project-owned files**. If the saved policy is no longer needed, this exact command removes that backup:

```sh
sudo rm -f /etc/usbgate/demo.json.disabled
```

Use it only after verifying it is your own recovery backup. It does not remove other files, the installed program or the Git checkout. Never delete shared system directories or unrelated contents.

## Emergency recovery without Python

If the worker reports `unsafe to stop`, inspect the effective demo unit and its dependencies before issuing a manual stop. See [recovery diagnostics](docs/recovery.md).

If the CLI, policy or Python fails, **do not depend on the USB stick to recover**. The following uses systemd and shell commands, controls only the project-owned demo, and was exercised on the physical notebook.

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

The last `mv` applies when a live `demo.json` exists. If it has already been moved, **do not overwrite an existing backup**. Inspect and preserve it separately. These steps do not remove the installation; once the timer and service are confirmed inactive and the live policy is absent, run `sudo make uninstall` from the source checkout to remove manifest-owned files.

Verify:

```sh
sudo systemctl is-active presence-demo.service
sudo systemctl is-active usbgate-reconcile.timer
sudo /usr/local/sbin/usbgate demo status
```

Expected: `inactive`, `inactive`, and `state: unconfigured`, provided the CLI is still installed. If the CLI is broken, the two systemd checks still work. The CLI may be missing after uninstall; that is expected. See [detailed recovery notes](docs/recovery.md).

## Can I protect my own services?

**Not directly with this release.** The commands `demo enroll` and `demo enable` always target the fixed, project-owned **`presence-demo.service`**. The `inspect-unit` command is only a conservative, read-only check; it **does not enroll** any unit. There is **no** command such as `enroll my-app.service`, no general socket handling, and no multiple-service policy engine.

The bundled service runs `/usr/bin/sleep infinity` under a systemd dynamic user. It is intentionally disposable.

**For development in a separate fork**, a maintainer can adapt the *source* of the demo unit to launch a different **independent, noncritical, foreground test program**, then redo review and all safety tests before installation. This **replaces the demo workload**; it does not attach the gate to an existing systemd service and does not add a second controlled unit. Do not edit an installed unit in place: the manifest and integrity checks deliberately reject changed installed files. Read [the extension guide](docs/extending.md) for the exact supported boundary and a cautious development workflow.

Controlling arbitrary services or sockets would require a new implementation with explicit service ownership, dependency checks, safe activation and restart behavior, and tested fail-closed recovery. That expansion is **possible**, but **not implemented or scheduled**. See [the completion and future-scope notes](docs/completion-plan.md).

## Troubleshooting

Start with these **read-only** commands:

```sh
sudo /usr/local/sbin/usbgate doctor
/usr/local/sbin/usbgate scan
sudo /usr/local/sbin/usbgate status --json
sudo systemctl status usbgate-reconcile.timer --no-pager
sudo systemctl status usbgate-reconcile.service --no-pager
sudo systemctl status presence-demo.service --no-pager
sudo journalctl -u usbgate-reconcile.service -n 60 --no-pager
sudo journalctl -t usbgate -n 60 --no-pager
```

| Symptom | Meaning and safe next action |
| --- | --- |
| `scan` shows no suitable stick | Confirm it is attached and is USB mass storage class `08`. A missing serial or duplicate identity cannot be enrolled. Do **not** bypass the checks. |
| `demo enroll` refuses the fingerprint | Copy exactly the 12-character key from `scan`, not the `vid_pid` value. The device must currently be present, unique and `identifier-only`. |
| `demo enable` says observation/timer is unavailable | Run `doctor` and confirm the timer is `active`. After installation, `monitor enable` must precede demo enablement. |
| `demo enable` says the installed unit fails preflight | Run `sudo systemctl daemon-reload` and `inspect-unit presence-demo.service`. Do not change or overwrite a managed file directly. |
| Service remains `inactive` while policy says `enabled` | The policy may be armed without a valid present device. Check `scan`, `status --json`, timer and journal. Do not override the grant manually. |
| Service does not stop after 10–20 seconds | The grace starts **after detection**; timer fallback can take longer. Check timer and journal. If reliable closure matters, use [manual recovery](docs/recovery.md); do not rely on this as a security boundary. |
| `sudo systemctl start presence-demo.service` leaves it inactive | With the grant missing, `ConditionPathExists` deliberately prevents a normal manual start. This was verified on hardware. |
| `make install` refuses an occupied path or existing manifest | An installation or another file already owns that path. Inspect ownership and the manifest; do not overwrite unknown files. |
| `make uninstall` refuses | Disable/reset the demo, disable observation, stop project units and verify the installed file hashes. A policy backup moved aside during recovery is intentionally retained. |
| `demo status` says policy corrupt or a systemd command fails | Stop the demo through [Python-independent recovery](docs/recovery.md), preserve the files for inspection, and do not bypass integrity checks. |
| An expected command is missing after uninstall | This is normal: the installed launcher and units were removed. Use the source checkout to reinstall if needed. |

A stopped or failed systemd unit, missed udev event, kernel failure, broken timer or unavailable manager can leave availability inconsistent. The CLI is diagnostic, **not** a guarantee of successful enforcement.

When reporting an issue, include the Debian/systemd/Python versions, the command, exit status, redacted console output and relevant logs. **Remove hostnames, IPs, raw serials and real fingerprints** from public reports. See [troubleshooting and recovery](docs/recovery.md).

## Limitations and future possibilities

- **Spoofable identity:** USB vendor ID, product ID and reported serial are not secret, unique or tamper-resistant. Short hashes are for correlation, not identity proof.
- **No content challenge:** no files are read from the USB; no passwords, encryption keys, FIDO2, TPM, PAM or hardware-backed authentication are used.
- **Single disposable unit:** only the bundled `presence-demo.service` can be started/stopped; no generic service/socket control, no multi-policy or production integration.
- **No hard stop deadline:** the 10-second grace follows detection; missed events, timer scheduling, blocked worker/manager and actual process termination add delay, potentially unbounded.
- **Systemd condition scope:** `ConditionPathExists` is checked on service start. Removing a grant alone does **not** stop a running service; the worker must request and verify a stop. Root administrators can bypass the demonstration.
- **Partial failure coverage:** normal insertion/removal, reconnection, blocked manual start, reboot and emergency recovery were physically demonstrated. USB removal *within* grace, timer-only wakeup isolation, corrupt policy on the real host, hostile USB cloning and major process crashes were **not**.
- **Test-host scope:** Debian 13/systemd 257 and Python 3.13 on a low-resource physical notebook. Other distributions, architectures and production workloads are outside the validation record.

**Development is paused after this experimental milestone.** Possible future work includes measured fallback latency, deeper failure injection, a safe generic opt-in service adapter and cryptographic token research. None of these are present in this release. See [technical boundary](docs/demo-safety.md) and [future scope](docs/completion-plan.md).

## Evidence, documentation and credits

- [Disposable service gate: physical tests and safety boundaries](docs/demo-safety.md)
- [Initial USB observer: physical notebook evidence](docs/hardware-validation-2026-11-22.md)
- [Python-independent recovery](docs/recovery.md)
- [Adapting the demo for a custom test workload](docs/extending.md)
- [Threat model and exposure](docs/threat-model.md)
- [Prior art and acknowledgments](docs/prior-art.md)
- [Historical design exploration](docs/phase0-review.md)

The idea and requirements originated with the maintainer. **AI-assisted tools contributed to architecture review, code, tests and documentation**; the maintainer reviewed changes and ran the physical Debian notebook trials. Results are reported as tests, not as a security certification.

Inspired by **Henrique ([@rique-decoder](https://github.com/rique-decoder))** and his educational [Linux USB Security Token](https://github.com/rique-decoder/linux-usb-security-token). This implementation was developed independently and does not include upstream source code. [USBGuard](https://github.com/USBGuard/usbguard) is a separate project for USB device authorization.

Released under the [MIT License](LICENSE).
