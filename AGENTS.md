# Maintainer instructions

## Release scope and project state

USB Presence Gate is an experimental Python USB-presence lab for a
headless Debian 13 host. On 2026-11-22 the maintainer physically verified
the observer and **one fixed, project-owned disposable service gate**,
`presence-demo.service`. The current milestone is complete and development
is **paused**, not permanently abandoned.

The current CLI **does not** support arbitrary service/socket enrollment,
multiple policies, USB cryptographic authentication, or production service
enforcement. Device descriptors are spoofable; a fingerprint is not an
authentication factor. Future expansion needs new code, tests and human
approval, not just documentation changes.

## Working rules

- Reply to the maintainer in Brazilian Portuguese, plain and concise.
  Everything in the repository is English: code, comments, README, docs,
  tests, commits, PR descriptions and CLI help.
- Never commit directly to main, merge, silently rewrite published history
  or activate services without the maintainer's approval. Work in reviewed
  topic branches and PRs. Do not start new feature development unless asked.
- Label validation honestly: untested, offline-tested, CI-verified or
  hardware-verified with actual output supplied by the maintainer.
  Hardware evidence for the existing demo does **not** transfer to new
  workloads or revisions.
- Never commit raw USB serials, device-specific fingerprints, private IPs,
  real hostnames or other identifying machine data. Use fictional examples.
- Keep complete, copy-pasteable README procedures for install, scan,
  observation, enrollment, demo enable/test, status, disable/reset, manual
  recovery and uninstall. Document failure modes and intentional leftovers.
- Credit inspiration and prior art without misrepresenting upstream code
  ownership or licensing. Disclose AI-assisted development.

## Implemented platform

- Debian 13 (Trixie), systemd 257, Python 3.13 standard library only.
  Small oneshot worker activated by udev and a systemd timer. No resident
  Python daemon, VM, GUI, containers, USB mounts, PAM or FIDO2.
- Observation reads Linux USB sysfs only and does not access files on
  the USB stick. The optional demo accepts one present, unambiguous
  mass-storage descriptor fingerprint with serial and one opt-in policy.
- Only `presence-demo.service` can be controlled by the current demo.
  The unit starts an idle `sleep` process under `DynamicUser=yes`.
  The installed manifest, unit and grant are guarded by integrity checks.
- A configured 10-second *detection-relative* absence grace is not a
  physical unplug-to-stop deadline. Timer fallback and manager failure
  may add unbounded delay.
- The Python-independent recovery commands live in
  [docs/recovery.md](docs/recovery.md); [docs/extending.md](docs/extending.md)
  explicitly distinguishes source adaptation from unsupported general
  service enrollment.

## Hard safety constraints for future changes

- Never touch SSH, network, firewall, PAM, GRUB, fstab, system login,
  core systemd processes, Docker engine or authentication.
- Protect canonical names **and aliases** of critical services:
  ssh*, sshd*, systemd-*, dbus*, networking, NetworkManager*,
  wpa_supplicant*, getty@*, serial-getty@*, console-getty*,
  user@*, rescue*, emergency*, nftables*, ufw*, iptables*,
  netfilter-persistent*, fail2ban*, apparmor*, auditd*, rsyslog*,
  chrony*, ntp*, systemd-timesyncd*, usbgate-*, docker* and
  containerd*.
- Never connect USB-controlled strings to shell, paths or systemctl
  arguments. No shell, eval or shell=True. Never mount, read or write
  the USB filesystem or change USB kernel authorization.
- Any future generic gate requires exhaustive dependency, alias,
  activation and stop-propagation review; explicit operator ownership
  and reversible changes; root-owned durable state; serialized
  transitions; verified stop outcomes; and Python-independent recovery.
- Do not claim fail-closed behavior beyond tests and system boundaries.
  Kernel, systemd, timer, worker and USB spoofing failures remain relevant.
- Preserve only manifest-owned removal; never force-delete foreign
  or modified system files.

## Historical architecture notes

[docs/phase0-review.md](docs/phase0-review.md),
[docs/lifecycle.md](docs/lifecycle.md) and
[docs/spike-procedures.md](docs/spike-procedures.md) describe earlier
**proposals and experiments**, some of which were retired. These are not
user-facing instructions for the current implementation. The README and
current source code define implemented behavior.
