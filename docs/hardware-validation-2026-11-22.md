# Physical Debian 13 notebook validation — 2026-11-22

This is a concise evidence record of commands executed by the maintainer on the physical headless notebook over SSH, **before the follow-up hardening commit**. Identifiers and addresses are intentionally omitted.

## Environment

- Host: Positivo Motion; Intel Atom x5-Z8350; 2 GB DDR3; Debian 13 headless.
- Python 3.13.5; systemd active; USB sysfs available.
- A 14.6 GiB-class USB storage stick with a reported USB serial and interface class `08`.
- The observer did not mount the USB device, and no non-project service was enrolled or controlled.

## Observations

| Procedure | Maintainer-supplied result |
| --- | --- |
| `make test` | 10 unit tests passed (0 failures). |
| `PYTHONPATH=src python3 -m usbgate.cli scan` | Storage device recognized with class `08`, `identifier-only`, and a redacted fingerprint. |
| `PYTHONPATH=src python3 -m usbgate.cli doctor` | Python/systemd/sysfs available; package, observer and timer initially absent. |
| `sudo make install` | Inert files installed; observer remained disabled. |
| `/usr/local/sbin/usbgate doctor` | Installed CLI ran; package installed; timer and observer not enabled yet. |
| `sudo /usr/local/sbin/usbgate monitor enable` | Successful; `status --json` reported `observe`, timer active and the USB device `present`, enforcement false. |
| Physical unplug | `status --json` reported the target `absent`; other USB entries remained `present`. |
| `sudo journalctl -t usbgate -n 30 --no-pager` | `device_absence_pending` at 13:57:47, `device_absent` at 13:57:57, and `device_returned` at 13:59:13 (local time). |
| Physical replug | The same fingerprint returned to `present` with `absent_since: null`. |
| `sudo /usr/local/sbin/usbgate monitor disable` | Successful; `doctor` reported observer disabled, timer inactive, and cached state still available. |
| `sudo make uninstall` and `sudo systemctl daemon-reload` | Successful; post-uninstall checks showed launcher, systemd units, udev rule and manifest removed. |

## What these results do not establish

- No claim is made about cryptographic authentication, unique hardware identity, or resistance to cloned USB descriptors.
- The test did **not separately prove which wakeup mechanism** (udev or the periodic timer) initiated each reconcile.
- Boot with the stick inserted, rapid replug within grace, a second device exposing identical descriptors, repeated simulated failures, and power interruptions remain separate tests.
- No service or socket gating exists in this PR. SSH, networking, PAM and firewall were out of scope.
- The follow-up hardening patch has separately passed GitHub Actions unit tests and source compilation. Its changed installation behavior has not yet been retested on physical hardware.

This document records a single completed session, not a blanket certification for future revisions.
