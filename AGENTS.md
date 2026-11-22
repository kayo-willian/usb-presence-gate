# Maintainer instructions

usb-presence-gate is a small physical-presence interlock for explicitly enrolled, noncritical systemd units on Debian 13. USB descriptors give identifier-only assurance and can be cloned. This is a useful lab tool, not a security product. Keep it small.

## Working rules
- Reply to the maintainer in Brazilian Portuguese, short and plain, no jargon, one step at a time. Everything in the repository is English: README, docs, code, comments, CLI help, commits, PRs.
- One small step per topic branch and PR. Never commit to main, merge or rewrite published history. Do not start the next step before the maintainer approves.
- Label status honestly: untested (default), unit-tested, ci-verified, hardware-verified (only with output pasted by the maintainer from the target notebook). Never present simulated results as hardware results.
- No real serials, UUIDs or device names in the repo; use fictional ones. Credit prior art in README and docs/prior-art.md. Do not copy third-party code without checking its license.
- The README must disclose AI assistance and contain exact, copy-pasteable commands for every operation: install, setup, enroll, enable, test, status, disable, recover, uninstall. Mark each command block untested until the maintainer reports it works.

## Scope (MVP)
- Target: Debian 13 (trixie), systemd 257, Python 3.13 standard library only. No resident daemon, Docker, VM, GUI, LUKS, multi-distro, Zabbix or FIDO2.
- Controlled unit types: service and socket only. One policy per unit. Absence of the device always closes the gate; there is no option to keep a service running without it. Weak (serial-less or ambiguous) devices are rejected, not enrolled.
- Design reference: docs/phase0-review.md and docs/lifecycle.md. The experiments S3/S4, gate G1 and most of the hypothesis ledger are retired. If a simplification here conflicts with those docs, this file wins.

## Safety rules (never relax)
- Never touch SSH, network, firewall, PAM, GRUB, fstab or system authentication.
- Never control denylisted units (canonical names and aliases): ssh*, sshd*, systemd-*, dbus*, networking, NetworkManager*, wpa_supplicant*, getty@*, serial-getty@*, console-getty*, user@*, rescue*, emergency*, nftables, ufw, iptables*, netfilter-persistent*, fail2ban*, apparmor*, auditd*, rsyslog*, chrony*, ntp*, systemd-timesyncd*, usbgate-*.
- Before enrolling a unit, check its dependencies, aliases and conflicts; refuse if starting or stopping it could affect a critical unit.
- Only systemctl start/stop on enrolled units and project units. Never isolate, reboot, poweroff, kill or udevadm trigger. No shell, eval or shell=True; fixed argument lists. USB strings are hostile and never reach commands or paths.
- Never mount, read or write the USB device. Do not change kernel USB authorization.
- Runtime reads only the applied snapshot and the registry, never the hand-edited TOML. If they are unreadable, close the gates (fail-closed); never leave services open.
- After a close request, verify the result; do not trust --no-block alone. Report failures.
- Recovery must work without Python, without the USB device and without the CLI (docs/recovery.md). Uninstall removes only manifest-owned files.
- Root-owned files, atomic writes, shared lock, never follow symlinks.
