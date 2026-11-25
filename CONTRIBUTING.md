# Contributing to USB Presence Gate

[Português (Brasil)](pt-BR/CONTRIBUTING.md)

Contributions are welcome. You can fork this repository, experiment independently, report a bug, improve documentation or submit a pull request. The project is licensed under [MIT](LICENSE); these guidelines govern contributions to this upstream repository, not what you may do with your own fork under that license.

## Project scope

USB Presence Gate is an experimental USB descriptor observer and an opt-in gate for one disposable service on headless Debian 13. It is not authentication, a security product or a general-purpose service manager. Read the [README](README.md), [safety boundaries](docs/demo-safety.md), [recovery guide](docs/recovery.md) and [maintainer instructions](AGENTS.md) before changing behavior.

Helpful contributions include reproducible bug reports, regression tests, USB observation accuracy, bounded resource usage, safe failure handling, documentation and independently verified hardware observations. Discuss architectural changes, new dependencies or broader service control in an issue before implementation. A proposed feature is not a commitment to merge it.

## Getting started

Use a regular account on a Linux development machine. The reference platform is Debian 13 with systemd 257 and Python 3.13. The offline suite also supports testing with Python 3.12. No USB device, root access, running systemd, Docker, VM or third-party Python package is needed for the offline tests.

1. Fork the repository using GitHub's **Fork** button and clone your fork.
2. Add the original repository as the upstream remote and create a focused topic branch.

   ```sh
   git clone https://github.com/YOUR-USERNAME/usb-presence-gate.git
   cd usb-presence-gate
   git remote add upstream https://github.com/kayo-willian/usb-presence-gate.git
   git fetch upstream
   git switch -c fix/descriptive-name upstream/main
   ```

3. Run the existing tests before changing the code.

   ```sh
   make test
   python3 -m compileall -q src bin tests
   ./bin/usbgate --help
   ```

4. Make the smallest coherent change, add regression tests where applicable, and rerun the full suite. For documentation-only changes, check links, commands, technical accuracy and the diff.
5. Review and commit your changes, push the branch to your fork, and open a pull request against this repository's `main`.

   ```sh
   git diff --check
   git status --short
   git add -- path/to/changed-file
   git commit -m "fix: describe the change"
   git push -u origin fix/descriptive-name
   ```

Replace the example username, branch name and file path with your own. Use `docs/`, `fix/` or `feature/` branch prefixes as appropriate. Keep commits descriptive and avoid unrelated changes.

## Safety requirements

- Keep demo actuation restricted to the bundled `presence-demo.service`. The observer may manage only its own fixed monitoring units and rule.
- Never interfere with SSH, networking, firewalls, authentication, PAM, boot configuration, Docker, logging, unrelated systemd units or kernel USB authorization.
- Never mount or access USB filesystem contents. Treat descriptors and fingerprints as untrusted, spoofable identifiers; never use them as shell commands, paths or arbitrary unit names.
- Preserve verified unit identity and integrity, explicit unknown-state handling, administrative locking, authorization inhibition, rollback, timer fallback, grant revocation and safe stop verification.
- Preserve Python-independent recovery and manifest-based ownership checks. Do not bypass a refusal by force-deleting files or weakening a safety check.
- Keep runtime use small, retain the standard-library architecture and do not introduce a resident daemon or new dependencies without prior discussion.
- Do not claim that an unplug guarantees a stop within ten seconds. The grace period starts at detection, and failures can leave the process active.

For unit and integration tests, use temporary directories, simulated USB observations, controlled manager responses and deterministic failure injection. Test failure paths as well as successful operations. For concurrent changes, demonstrate ordering with real locks and explicit synchronization where feasible. Do not stop real services or change actual hardware as part of the offline suite.

Live experiments are optional for contributors. If you choose to validate on your own disposable test host, read the recovery guide first, maintain a separate SSH session and local console access, and never test against a critical workload. Do not claim hardware validation based on simulation or an older revision. Report the exact commit, platform, procedure, result and remaining limitations.

## Reports and proposed changes

Search existing issues and pull requests before opening a new one. Use the bug report or feature proposal template. For a bug, include the commit, operating system, Python and systemd versions, reproduction steps, expected and actual behavior, and redacted output. For a proposal, explain the problem, alternatives, scope and safety implications.

Do not publish real USB serials, fingerprints, hostnames, IP addresses, credentials or private logs. Use fictional identifiers in tests and examples. Report suspected vulnerabilities through [SECURITY.md](SECURITY.md), not a public exploit report.

## Review checklist

Before submitting a pull request:

- Explain the problem, solution, affected behavior and any tradeoffs.
- Keep internal technical documentation, CLI help, code comments, commits and PR descriptions in English. Community-document translations belong in `pt-BR/` and must stay aligned with the English originals.
- Use readable, focused code and the existing project conventions.
- Preserve existing regression coverage; add tests that would fail before a bug fix.
- Report exact validation performed, including failures or checks not run. A passing offline suite does not establish hardware safety.
- Update affected documentation and the Unreleased section of [CHANGELOG.md](CHANGELOG.md) for user-visible or significant safety changes.
- Disclose material AI assistance in the PR, including which parts it helped produce. Verify the proposed changes yourself; do not invent authorship, test results or upstream attribution.
- Submit only work you have the right to contribute under the MIT license. Preserve copyright notices and identify external material and its licensing.

PRs are reviewed before merge. The maintainer may request changes or decline proposals outside the project's scope. Do not merge on the maintainer's behalf or rewrite shared history without approval. Review and response times are not guaranteed.

Follow the [Code of Conduct](CODE_OF_CONDUCT.md) in project discussions. Respectful technical disagreement is welcome.
