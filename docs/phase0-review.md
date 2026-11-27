> **Historical architecture research, not current operational instructions.** The implemented 2026-11-22 milestone deliberately supports only USB observation and the fixed disposable `presence-demo.service`. See [README](../README.md) and [current scope](completion-plan.md).

# Phase 0 design review

**Historical review.** The current MVP covers services and sockets. G1 and experiments S3/S4 are retired. The [maintainer instructions](../AGENTS.md) define the current scope, and the [lifecycle](lifecycle.md) records the selected gate and trigger.

**Approved scope (2026-11-22).** The maintainer authorized observation and preparation of S1-lite (service and socket) and S2-lite (add, remove, boot with the stick, rapid reconnect, removal followed by silence). The remaining experiments require separate approval. The USB gate, trigger, enforcement and recovery semantics still require evidence. All proposed runtime behavior is `untested`.

## Repository and name check

Reviewed on 2026-11-22 at [bdc80c9](https://github.com/kayo-willian/usb-presence-gate/commit/bdc80c9e955864186142f12eb3baf105482da022). The private repository contains a two-line README, an MIT license and a Python .gitignore. There is no implementation, CI workflow or hardware record to assess. The README describes the intended utility. It does not establish that service control works.

| Namespace | Lookup and finding |
| --- | --- |
| GitHub | An authenticated repository search for `usb-presence-gate in:name` returned only this repository. The owner/name is already held by the project. Other owners can use the same basename, and search visibility is limited. |
| Debian | The [archive query](https://api.ftp-master.debian.org/madison?package=usb-presence-gate) returned HTTP 200 with zero rows. The same query for usbguard returned archive rows. The exact name was also absent from the [Trixie binary package list](https://packages.debian.org/trixie/allpackages?format=txt.gz) and [sid binary package list](https://packages.debian.org/sid/allpackages?format=txt.gz), both of which contained usbguard. |

Keep the proposed name. These are dated namespace checks. They do not reserve a future package name. See [prior art](prior-art.md) for attribution.

## Risks in order of consequence

| Severity | Failure and consequence | Required evidence or design change |
| --- | --- | --- |
| Critical | A failed reconcile can leave an open flag. Stopping an instance leaves the flag on disk. A later start can again satisfy the condition. A broken drop-in can leave a protected service running even after a successful gate stop. | S1 and S4 must cover reactivation and broken bindings. Serialize against in-flight opens, delete owned grant flags before submitting gate stops, then verify closure. The emergency path must work independently of the snapshot and Python. Keep the incident open if closure cannot be observed. |
| Critical | Rejecting a critical name on input does not bound the systemd transaction. An alias, a later drop-in, a dependency of a dependency with a critical conflict, stop propagation, or a unit's own stop action can affect remote administration. | Match canonical IDs and all names, with suffix-aware deny rules. Check the effective start and stop graphs, activation sources, propagation and conflicts at every relevant node. Inspect local administrator-owned unit behavior. Reject an unresolved safety check before enrollment. Review runtime drift separately from the response to it. |
| High | After a lost snapshot, S2 can be mistaken for S0/S1. An update can also leave two policies claiming one unit, or snapshot membership different from loaded drop-ins. | Use the marked, root-owned per-unit drop-ins themselves as the enrollment inventory. Enforce one owner per canonical unit and activator. Compare the loaded relationships with intended membership. Treat disagreement as DEGRADED. |
| High | A restart can interrupt the worker between flag creation, start, verification and state persistence. Repeated restarts can starve all progress. Restarts that reset the absence clock can extend grace indefinitely. | Persist first absence before waiting. Have the worker wait the remaining grace and rescan before deciding, including a single removal with no later event. Bound retries and prove progress under bursts in S2/S3 before choosing a timer default. |
| High | A pending stop, an active socket, an outstanding start job, or an unreadable bus can be reported as closed. Reusing the same failed bus in OnFailure cannot establish containment. | Verify the activators, gate and member outcomes under one deadline. Distinguish requested closure, observed closure and unknown exposure. S3/S4 must exercise the unresolved outcomes. |
| High | Interruption during enable, disable or recovery can leave a live dependency after its file is removed. Stopping the gate at that point can stop a service the operator intends to preserve. | Serialize transitions and worker access, verify effective detachment after reload, and make partial progress discoverable. Test retry and manual recovery with a disposable active service. |
| Medium | Partial USB enumeration, duplicate descriptors or a rescan after suspend can turn stale presence into a new grant. Short USB identifiers are also easy to correlate in logs. | Cap pending enumeration, refuse ambiguous identity, rescan after resume, sanitize logs and test absence using the same boot clock. Record only redacted evidence. |
| Medium | Unbounded per-unit waits, worker churn and repeated unknown-device logs compete with SSH and journald on the Atom. | Measure end-to-end completion, CPU, RSS, journal growth and access to the host. Use one transaction deadline. Select limits from evidence. |

A critical consequence blocks real control even when its likelihood on this notebook is unknown. No experiment in this phase measured that likelihood.

## Decisions for sections 5 and 6

| Plan item | Disposition and rationale |
| --- | --- |
| 5, reconciliation | Retain the level-triggered, idempotent design and absence of a resident process. Read current observations on every run. A separate liveness argument is needed for each deferred action. |
| 5.1, reconcile service | Retain a root oneshot, incremental hardening, availability exit 3 and critical-failure handling. Verify whether a cancelled or timed-out job invokes OnFailure. Size TimeoutStartSec for lock acquisition, settle, grace work, dispatch and verification across the entire run. Treat unlimited starts on each unit as a hypothesis. |
| 5.1, timer | Retain a configurable safety scan. An interval measures only part of detection latency. Require a running safety timer in lifecycle S2. Calibrate its interval on hardware. The worker handles grace expiry within its own invocation. |
| 5.1, fail-closed service | Retain the approved narrow scope and Python-independent path. Delete the owned grant flags before stopping the gates, including flags for currently unloaded instances. A glob matches primary names of loaded units and an empty match may be silently skipped. A template, alias, canceled job or later activation cannot be covered by assuming the stop queued everything. Compare the manager's inventory with trusted local ownership. [Trixie systemctl manual](https://manpages.debian.org/trixie/systemd/systemctl.1.en.html) |
| 5.1, gate and drop-ins | Keep the oneshot template with RemainAfterExit as the S1 candidate. ConditionPathExists is evaluated on start, so removing a flag alone cannot close an active gate. Test BindsTo with After, and separately with Requisite, for each supported type. Verify effective Id, bindings and ordering as well as DropInPaths. Detect shadowing and filename collisions. [Trixie unit manual](https://manpages.debian.org/trixie/systemd/systemd.unit.5.en.html) |
| 5.2, udev trigger | Retain the narrow usb_device add/remove filter, fixed arguments and short submission. Test restart against an already running worker. Queuing a new job does not guarantee a fresh scan completes. Measure cancellations and the longest interval without a completed check. [Trixie udev manual](https://manpages.debian.org/trixie/udev/udev.7.en.html) |
| 5.2, alternative | Keep SYSTEMD_WANTS as a contingency. Test the device tag, coldplug ordering, escaped sysfs instance, actual matching .device and removal stop callback. Only consider a shorter timer after measuring it on this host. [Trixie device manual](https://manpages.debian.org/trixie/systemd/systemd.device.5.en.html) |
| 5.3.1–3, lock and inputs | Retain exclusive flock and runtime reads limited to applied inputs plus owned state. Use one stable lock inode. A CLI holding it must release before waiting for a reconcile that also needs it. Define schema, canonical hash input and version for both files. A checksum detects corruption under the trusted-root assumption. Missing data in an armed installation is critical. An empty valid registry grants nothing. |
| 5.3.4–6, scan and decision | Retain bounded settle and distinct pending/mismatch states. Count interfaces of the active configuration for the same device, including unbound interfaces. Never grant on partial data or continuously extend existing grace on repeated partial reads. Any complete, active match may grant. Persist absent_since against CLOCK_BOOTTIME in the same boot. Wait only the remaining grace, rescan at expiry, and clear the absence record on observed return. Treat lost timing state conservatively. |
| 5.3.7–9, actuation | Retain flag-before-open, flag-removal-before-stop, gate verification and explicit fallback limited to trusted enrolled members. Revalidate identity and generation before starting members. The enabled subset controls action. Apply on_present=start only on the transition to granted. A later scan of a granted policy preserves a manual stop. |
| 5.4, verification | Retain asynchronous submission with independent verification, exits 0–4 and the prohibition on extra kill escalation. Define per-type properties and a global deadline including start and queue times. An infinite/missing timeout or unknown state needs an explicit outcome. Use the precedence below. |
| 5.5, Python modules | Retain the proposed stdlib boundaries. The pure reconciler takes observations and returns decisions. The integration layer owns time, locking, I/O and subprocesses. Document the deliberately separate fixed systemd/udev emergency calls. |
| 6, stdlib and host boundaries | Retain Python stdlib and verify the actual interpreter includes tomllib. Keep USB content, mounting, kernel authorization, system authentication and policy-supplied commands outside the design. Reject unknown keys, options disguised as unit names and commands derived from USB input. |
| 6, absence and invalid inputs | Retain mandatory closure on absence and the snapshot boundary. Use grace only for physical uncertainty. Revocation removes eligibility immediately. If another valid device still qualifies, the grant continues. Otherwise close without grace. Critical integrity failures require emergency closure. Weak devices are observation-only. Invalid editable TOML has no runtime effect. |
| 6, project scope | Retain Debian 13 CLI scope. Keep LUKS, multi-distribution support, a resident daemon and Zabbix integration outside the core. FIDO2 requires a separate Phase 5 decision. |

### Verification precedence proposed for S3

| Observation | Classification |
| --- | --- |
| Closed desired, gate and every enrolled activator/member inactive with no reopening job and effective bindings verified | Closed, exit 0. Confirm that an unmanaged listener or surviving process is outside the claimed guarantee or refuse units with that behavior. |
| Stop pending, within deadline | Keep checking. Deactivating at expiry, active, activating, reloading, an unresolved job or unknown state at expiry means exposure, exit 4. |
| Active member with inactive gate, missing/effectively superseded binding, or a live activator behind a closed gate | Exposure, exit 4, including when another member only has an availability warning. A global daemon-reload indication triggers inspection of the affected effective configuration. |
| Closed desired and manager inspection fails | Exposure unknown, exit 4. Keep the diagnostic, invalidate grants where safely possible and retry when the manager returns. |
| Open desired and gate cannot activate, or an intended start fails, is masked or missing | Exit 3 if there is no exposure. For an allow-only policy an inactive member is permitted. Missing or masked units alone do not prove that every activator is closed. |
| Invalid trusted inputs in S2, unexpected worker failure or timeout | DEGRADED/exit 4 for detected inconsistency. Test manager-level failure handling separately for a worker that cannot return an exit code. |

### Other contradictions to resolve before control

- Section 9.1 references a missing section 5.6. The dependency check is in 9.4. Its visible reverse graph may be incomplete for unloaded units. Define the eligible unit set conservatively, including critical aliases, indirect conflicts, stop propagation, activation through other services and failure actions. If drift makes stopping dangerous, deny new opens, report unresolved exposure and require operator recovery. Automatic closure and preserving a newly coupled critical service cannot both be guaranteed.
- The section 10 verb list omits manager reads, timer enable/disable and the fixed udev restart. Define lifecycle, read-only, actuator and emergency permissions separately. Bare names in the denylist must cover the intended unit suffixes. Reject leading hyphens and use an end-of-options boundary when applicable. Only fixed project units may use the reserved internal namespace.
- Snapshot application and policy enablement are distinct. Applying a snapshot alone must never arm an S1 installation. Monitoring is specified in both Phase 1 and Phase 3. Phase 1 should exercise observation and disposable spike fixtures only. Stage production lifecycle transitions after G1.
- The final human decision retires confirm, --confirm-within and the systemd-run rollback. H22 is retained as a historical row. Manual recovery must still work with a missing CLI or untrusted snapshot. Manual recovery may reload udev rules after removing the owned rule.
- Define absent versus intentionally empty registry and classify duplicate or missing serials before enrollment. Weak observations cannot grant access.
- Enforce directory-component ownership and descriptor-based file checks. fsync both file and parent directory for durable persistent changes. Reserve project-owned filenames, detect foreign drop-ins, and validate manifests against installation roots. An identical uninstall tree and deliberate retention of registry/configuration are different acceptance criteria. Compare the managed tree and enumerate retained data.
- Specify who may read status and events when authoritative files are mode 0600. An unprivileged status view must not reveal raw identifiers. Separate audit of state transitions from repeated samples and bound unknown-device volume. Plan for journal rate limiting and volatile storage.

## Maintainer decisions

The marked drop-ins form the enrollment inventory. Each canonical unit belongs to one policy. Recovery may reload udev rules. Uninstall compares only the managed tree and lists retained data. The maintainer confirmed removal of `--confirm-within`, `confirm` and the dead-man switch. Timer configuration, grace, revocation and transition-only starts are recorded above.

Open evidence questions include cancellation behavior, effective dependency propagation, timer cadence and the safe response when manager state cannot be observed.

[Agent rules](../AGENTS.md) · [Threat model](threat-model.md) · [Lifecycle](lifecycle.md) · [Hypotheses](hypotheses.md) · [Spike outlines](spike-procedures.md)

Approval covers only the two lite spikes above. G1 later requires human-pasted S1–S4 evidence and a recorded human decision on trigger and gate form before either Phase 2 or Phase 3.

[Português (Brasil)](../pt-BR/docs/revisao-fase-0.md) · [Project overview](../README.md)
