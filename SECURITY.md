# Security Policy

[Português (Brasil)](pt-BR/SECURITY.md)

## Scope and limitations

USB Presence Gate is an experimental USB-presence observer with one opt-in disposable service. It is not cryptographic authentication, USB device authorization or production protection. USB descriptors can be copied, and neither a grant file nor the configured absence grace guarantees termination of a running process.

The reference platform is Debian 13 with systemd 257. The current development branch is `main`. This project has no promised support period, patch schedule or security response SLA. Historical hardware evidence applies only to the revision and scenarios tested.

## Reporting a vulnerability

Examples of relevant findings include unsafe service actuation, unintended effects on unrelated units, unexpected authorization after a failed administrative operation, integrity-check bypasses, unsafe privileged file handling and sensitive data exposure.

Use the repository's [Security Advisories page](https://github.com/kayo-willian/usb-presence-gate/security/advisories) and **Report a vulnerability** if private vulnerability reporting is available. If it is not available, open a public issue requesting a private contact method, without including exploit details, affected machine identifiers or secrets. Do not assume that private reporting is enabled.

Include the affected commit, environment, expected safety boundary, observed behavior, impact, minimal reproduction using simulated or disposable resources, and any suggested fix. Distinguish reproduced findings from hypotheses. Avoid publishing raw USB serials, fingerprints, hostnames, IPs or unredacted logs.

Please allow the maintainer a reasonable opportunity to investigate before making exploitable details public. Do not test against systems you do not own or have permission to test. There is no bug bounty or promised response deadline.

Ordinary non-sensitive bugs belong in GitHub Issues. The [contribution guide](CONTRIBUTING.md) explains safe testing and review. If a local installation behaves unexpectedly, use the [recovery guide](docs/recovery.md) rather than weakening safety checks or controlling essential services.
