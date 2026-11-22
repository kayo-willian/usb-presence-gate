# Completion plan

The original PR delivers hardware-verified **USB observation only**.
The observation release supports read-only inspection of potential systemd
service/socket members, with a strict denylist and conservative checks for
aliases, local ownership and direct stop relationships. A successful preflight
is not a safety proof. The next draft implements **only a disposable,
project-owned demonstration service gate**. It does not provide a general
policy engine or arbitrary service/socket enforcement.

## Outside the disposable-demo scope

1. **Generic enrollment:** explicit owner opt-in for other local disposable
   service/socket units; reject weak/duplicate USB identities and critical
   aliases. Not included in the demo release.
2. **Generic enforcement:** complete dependency validation, project-owned
   gates/drop-ins, strong process supervision and fail-safe transitions for
   arbitrary units. Not included in the demo release.
3. **Hardening beyond the demo:** exhaustive failure-injection tests and
   physical measurements of all stop-time bounds. Basic Python-independent
   emergency recovery and reversible uninstall were physically verified.
4. **Additional hardware acceptance:** fast reconnect within grace, timer-only
   fallback and corrupt-policy recovery remain unverified on the physical host.
   The demo's basic absent/present path, reboot, blocked manual start and
   emergency recovery were physically verified.
5. **Release:** review the final PR, confirm CI, and merge only on maintainer
   approval. USB descriptors are not cryptographic identities.

No network stack, SSH, firewall, PAM, Docker engine or monitoring service
may be enrolled. USB descriptors are clonable and offer only weak identity.
