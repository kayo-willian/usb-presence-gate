# Completion plan

The original PR delivers hardware-verified **USB observation only**.
This branch adds read-only inspection of potential systemd service/socket
members, with a strict denylist and conservative checks for aliases,
local ownership and direct stop relationships. It never enrolls or controls
any service; a successful preflight is not a safety proof.

## Remaining deliverables

1. **Enrollment:** explicit owner opt-in for one local disposable service or
   socket; reject weak/duplicate USB identities and critical aliases.
2. **Enforcement:** root-owned applied state, safe dependency validation,
   project-owned gates/drop-ins, serialized transitions, grace handling,
   post-stop verification and an active safety timer.
3. **Recovery:** interruption and failure tests; emergency recovery without
   Python or the USB device, and clean reversible uninstall.
4. **Hardware acceptance:** two SSH sessions, local recovery access, and
   disposable demo service only. Exercise absent, present, reconnect within
   grace, timer fallback, reboot, manual starts and clean recovery.
5. **Release:** code review, CI, accurate technical documentation, no
   unsupported security claims. Merge only on maintainer approval.

No network stack, SSH, firewall, PAM, Docker engine or monitoring service
may be enrolled. USB descriptors are clonable and offer only weak identity.
