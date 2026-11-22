# Maintainer instructions

This project is a physical presence interlock for explicitly enrolled, noncritical Debian 13 system units. USB descriptors provide identifier-only assurance. A human reviews each phase. Phase 0 is documentation only. Obtain written approval before changing phase. Only the human can settle a spike-dependent decision with dated target-host evidence.

## Evidence and publication

- Reply to the maintainer in Brazilian Portuguese. The English README must disclose the use of AI in the project.
- Use English for repository text, CLI help, code, comments, commit messages and PRs. Mark behavior untested by default. Use unit-tested for executed unit tests, ci-verified for an observed CI run and hardware-verified only for human-pasted date, command, output, kernel and device evidence. Redact identifiers before publication.
- Keep the hypothesis ledger current. Use fictional, labeled fixtures. Exclude real serials, UUIDs and device names. Attribute prior art and verify its licensing before considering reuse.
- Use a topic branch and an English PR describing changes, rationale, risks, checks and untested hardware behavior. Do not commit to main, merge or rewrite published history. G1 requires S1–S4 evidence and the human's gate and trigger decision.

## Runtime boundaries for later phases

- Keep SSH, network, firewall, PAM, GRUB, fstab and system authentication untouched. Only explicitly enrolled noncritical units, their owned drop-ins and project-owned resources are in scope. Preserve manual recovery. Obtain explicit authorization for destructive operations.
- Enforce the fixed denylist on canonical names and aliases, with critical transitive dependencies and conflicts checked before control. Protect ssh*, sshd*, systemd-*, dbus*, networking, NetworkManager*, wpa_supplicant*, getty@*, serial-getty@*, console-getty*, user@*, rescue*, emergency*, nftables, ufw, iptables*, netfilter-persistent*, fail2ban*, apparmor*, auditd*, rsyslog*, chrony*, ntp*, systemd-timesyncd* and usbgate-* from enrollment. Only service, socket, timer and path units qualify. Reject instances and Accept=yes sockets.
- Enforce absence closure. On critical failure, contain only the owned, protected scope. Runtime reads the applied snapshot and registry. Human-edited TOML belongs to check/apply. Forbid policy command hooks, shell execution, eval, arbitrary commands and device strings in commands or paths. Use validated fixed argv and allowlisted operations. Never issue isolate, reboot, poweroff, kill or udevadm trigger.
- Use root-owned safe paths, no-follow file access, safe ancestor checks, durable atomic updates and a shared lock. Restrict alternate sysfs roots to explicitly opted-in non-root tests. Validate each hardening claim. Protect third-party files and only manage the project's own drop-ins.
- Never mount, read or write USB media, alter kernel USB authorization or block devices. Keep dependencies to Python stdlib and native Linux facilities. Exclude a resident process, Docker, VMs, GUI, LUKS, multi-distro features and Zabbix in the core. FIDO2 requires separate approval. Keep the removed confirmation timer and dead-man switch outside the MVP.
