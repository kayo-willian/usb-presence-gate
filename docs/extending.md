# Extending the disposable demo (not a generic service gate)

**Current status: experimental milestone completed; active development paused.**
The real Debian 13 notebook tested only the bundled disposable unit.

## What can and cannot be done today

| Goal | Available now? |
| --- | --- |
| Observe USB devices without opening their filesystems | Yes |
| Enroll one unambiguous USB mass-storage descriptor for the demo | Yes |
| Start/stop the built-in `presence-demo.service` on physical presence | Yes |
| Replace its bundled `sleep` process in a **separate development fork** | Possible source adaptation; untested |
| Enroll an already installed app with `usbgate enroll my-app.service` | **No such command** |
| Gate multiple arbitrary units or sockets | **Not implemented** |
| Protect SSH, network, firewall, authentication or Docker engine | **Explicitly out of scope** |
| Prove USB authenticity with a key file or hardware cryptography | **Not implemented** |

The CLI's `inspect-unit` is a conservative **read-only preflight**.
It does not enroll, attach or control the inspected unit.

## Source-level adaptation: one noncritical foreground test workload

A maintainer who understands the safety limits may make a separate fork to
experiment with a personally controlled, **noncritical and disposable**
foreground process in place of `sleep`. This is **not** an officially
supported way to protect an existing systemd service, and changing the
demo invalidates the original hardware evidence.

1. Make a **new branch or fork** from a clean checkout. Do not edit the
   installed `/etc/systemd/system/presence-demo.service` directly.
2. Open `packaging/systemd/presence-demo.service` in the source checkout.
3. Change **only** the `ExecStart=` program to an independently audited,
   foreground-running, disposable absolute-path program. For example,
   `ExecStart=/usr/local/bin/my-disposable-worker` is a **placeholder**:
   it will not work until you supply and review that executable. Do not
   run an existing essential daemon or a service unit this way.
4. Retain `ConditionPathExists=/run/usbgate/demo-grant`, `DynamicUser=yes`,
   `NoNewPrivileges=yes` and the other sandbox properties. If your
   workload needs elevated privileges, network access or persistent data,
   **do not weaken these settings just to make it work**. That workload
   is outside this minimal demonstration.
5. Review unit dependencies, process lifecycle, signal handling, restart
   behavior and any possible access to SSH/network/system services.
   The static preflight is **not sufficient** for a new workload.
6. Run checks before installing onto an isolated **test host**:

   ```sh
   make test
   systemd-analyze verify packaging/systemd/presence-demo.service
   ```

7. If an earlier revision is installed, first perform its normal
   disable/reset/uninstall from the corresponding source checkout.
   Reinstall from the modified source only on a test machine. The
   installed manifest records hashes of managed unit files, and the
   gate deliberately refuses silent in-place edits.
8. Re-run the **full physical test matrix** for the new workload:
   absent/present, removal/grace, return, manual-start refusal, reboot,
   missed udev trigger, systemd failure, Python-free emergency recovery,
   and manifest-based uninstallation. If any test cannot be completed,
   document it as unverified. Never treat a new workload as covered by
   the existing `sleep` evidence.

This replaces the demo process **inside one fixed unit**, and its unit name
remains `presence-demo.service`. It **does not add additional services**.

## What a real generic service gate would need

A future release could introduce explicit, per-unit registration of owned,
noncritical systemd service/socket units. That is **new product design**,
not a documentation switch. It would require:

1. Canonical name and alias checks plus transitive dependency/stop-propagation
   inspection; keep a strict denylist of critical services.
2. Reversible project-owned unit integration, without modifying unrelated
   service definitions and without automatically taking over running units.
3. Durable enrollment and applied-state integrity, including interrupted
   transitions, duplicate USB identities and controlled manual recovery.
4. Prevention and detection of alternate activation paths (sockets,
   timers, paths, dependencies, manual starts), with verified stop outcomes.
5. Host-specific failure tests, reboot/rollback and measured event-to-stop
   latency on a disposable target before real data is involved.

**None of this generic functionality is implemented in the current
release.** Opening a future development PR does not require keeping this
experiment installed on a home server.

## USB files and authentication

No file or secret on the USB stick is required. Files on ordinary flash
media can be copied; simply adding a key file would not provide genuine
hardware-backed authentication. Such a feature would require a separate
threat model and protocol, and is not part of the current scope.

[Português (Brasil)](../pt-BR/docs/extending.md) · [Project overview](../README.md)
