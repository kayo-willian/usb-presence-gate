# Changelog

Significant changes to USB Presence Gate are recorded here. Entries describe merged changes; proposed work belongs in issues and pull requests. The source currently identifies itself as version `0.1.0`. The dated milestones below summarize development history, not separate tagged releases.

## [Unreleased]

### Added

- Contributor guide, code of conduct, security reporting policy, issue templates and pull request template.

### Changed

- Refresh installation, usage, diagnostics, update, recovery and contribution instructions in the README and align the detailed recovery guide. No runtime behavior changed.
- Systemd and udev safety verification ([#9](https://github.com/kayo-willian/usb-presence-gate/pull/9), 2026-11-24): check project-owned unit files and effective identities, direct transaction relationships, persistent timer enablement and deployed rule integrity against the installation manifest.
- Separate start and stop verification so a pending start can be stopped when the unit remains structurally safe; retain administrative inhibition until persistent monitor disablement is confirmed.
- Add monitor safety diagnostics and static verification of the three bundled systemd units in CI.

### Fixed

- Administrative consistency ([#8](https://github.com/kayo-willian/usb-presence-gate/pull/8), 2026-11-23): serialize administrative operations, use persistent authorization inhibition, commit activation after successful startup, disarm before shutdown and recover interrupted starts.
- Fail-safe reconciliation ([#7](https://github.com/kayo-willian/usb-presence-gate/pull/7), 2026-11-23): attempt closure on observation persistence failures, distinguish systemd states, independently report revocation and shutdown outcomes, check for active services without grants, strengthen uninstall checks and isolate the privileged launcher.

### Validation

- Offline regression suite expanded from 41 to 116 tests across the three hardening PRs. The latest CI also passed static unit verification. These changes still require live Debian 13 validation; no new hardware result is implied.

## 2026-11-22 — Experimental milestone

### Added

- Read-only USB descriptor observation with identifier-only, weak and ambiguous identity reporting.
- Opt-in udev and periodic systemd observation with volatile state and a detection-relative ten-second absence grace.
- Conservative read-only systemd candidate inspection and one explicitly enrolled, disposable service gate.
- Inert installation, manifest-based removal and Python-independent recovery.
- Physical notebook evidence and documentation for the supported demo, limitations, threat model and source adaptation.

### Validation

- Historical notebook trials covered the normal demo lifecycle, removal/reconnection, manual-start refusal without a grant, reboot with the stick connected, emergency recovery and manifest-based uninstall after recovery. See [hardware evidence](docs/demo-safety.md) for the exact scope.

[Unreleased]: https://github.com/kayo-willian/usb-presence-gate/commits/main/

[Português (Brasil)](pt-BR/CHANGELOG.md) · [Project overview](README.md)
