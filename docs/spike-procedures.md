# Phase 1 spike outlines

These are review procedures for future human execution. Phase 1 approval precedes fixture preparation. Use disposable, explicitly named noncritical fixtures only. Record the initial systemd/udev state, two independent SSH sessions, working network and local console before each trial. Stop the trial if any unrelated unit changes or access deteriorates. Do not trigger synthetic system-wide uevents or change host authentication. Arrange boot observations in a separately authorized maintenance window.

For every case paste the date, exact command, redacted raw output, kernel, systemd/udev versions and a fictional device label describing the tested device. Include desired state, monotonic timestamps, manager jobs, exit status, actual final state, SSH/network checks and fixture cleanup. Preserve timing and unit relationships when redacting identifiers. An omitted case stays untested.

## S1 — Gate semantics

1. Compare BindsTo plus After with the same fixture plus Requisite. Use a oneshot gate with RemainAfterExit and a disposable flag. Cover a service and its socket, timer and path activators.
2. With the flag absent and the gate inactive, attempt a direct member start and each supported activation. Capture condition result, job result, gate/member/activator state, listener and failed-unit list. Repeat with the flag present and then with an already-active gate.
3. Remove the flag from an active gate, inspect it, then request its stop. Verify all enrolled members and activators finish stopping, including a queued activation. Test a manual start afterwards and capture the outcome. Verify detachment preserves an active member before stopping a disabled policy's gate.
4. Observe normal boot with and without the device, including possible early starts. Record boot noise and SSH/network state. Flag any interval of service availability while closed. The human may select a variant only if reachability, closure and access preservation meet the intended behavior.

## S2 — Delivery, restarts and progress

1. In observe mode correlate physical add/remove, boot with the stick present, rapid reconnect, a single removal followed by silence, and a bounded burst with udev delivery, manager submissions and completed scans. Capture final physical state independently.
2. Arrange a second event during settle, during grace and during verification on disposable fixtures. Check whether first absence survives interruption and whether an expiry check actually runs. Compare timer enabled and disabled. Reconnect before expiry and check that stale absence cannot stop a valid policy.
3. Measure CPU, peak RSS, journal growth, event/worker/completion counts, lock wait and SSH responsiveness with StartLimitIntervalSec=0. Record when the final event produces a completed scan. Stop increasing the burst if host responsiveness deteriorates. Zero rate limiting earns no presumption of progress.
4. If the primary path fails, compare the tagged device-unit fallback under the same cases, verifying the mapping and removal callback. If considering timer-only operation, measure its detection delay and cost. The human selects the trigger after the observations.

## S3 — Asynchronous outcomes and deadlines

1. Capture per-type manager properties before submission, while jobs are queued, and after completion. Record a normal stop, slow deactivation within and beyond the deadline, failed activation, masked/missing member, pending start and competing jobs. Use fixture-local faults.
2. Exercise each row of the verification table in [the review](phase0-review.md), including a live activator, active member with inactive gate, stale effective configuration, unknown properties and an allow-only inactive member. Compare the observed listener with unit state. Repeat with multiple members and record a single end-to-end deadline.
3. Capture timeout and unavailable-bus classifications through a fixture-local failure or a test double if a real case would compromise the host. Mark simulated coverage separately. Never disrupt the host manager, SSH or network to manufacture an outcome. Verify that exposure outranks simultaneous availability failures.

## S4 — Emergency closure and recovery

1. Record the inventory of deliberately created gate instances, flags, loaded state and pending jobs. Compare no matches, multiple active matches, inactive/unloaded instances and an instance with a queued start. Capture exact glob arguments, selected units and subsequent states.
2. Compare an explicit critical worker exit, a timeout, an interrupted restart and exit 3. Observe whether OnFailure runs in each case and whether any gate can reactivate from a surviving flag. Include an active protected member whose disposable drop-in is absent. Success of job submission alone leaves the case open.
3. Introduce a missing/corrupt snapshot in the disposable enrollment and retain independent ownership evidence. Check that DEGRADED is visible, fresh grants are inhibited and only enrolled noncritical targets can be affected. Record any manager-unavailable case as unverified until scope-safe evidence is available.
4. Rehearse manual recovery without the CLI or USB device. Verify effective detachment before stopping gates, confirm the original member state, remove only fixture-owned artifacts and repeat recovery. Compare the baseline and verify both SSH sessions, network and local console.

**G1 decision record.** Attach S1–S4 evidence and H3–H8 observations, note skipped cases, identify the trigger and gate variant chosen by the human, and record unresolved exposure with its consequence. A failing safety case requires revision and another observation. Phases 2 and 3 need a written human decision.
