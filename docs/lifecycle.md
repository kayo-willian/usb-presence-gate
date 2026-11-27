> **Historical design proposal, not the implemented demo lifecycle.** This document describes an earlier generic gate architecture (including BindsTo/After and multi-policy ideas) that was not implemented in the finished experimental milestone. For real commands and supported behavior see [README](../README.md), [demo safety](demo-safety.md) and [recovery](recovery.md).

# Lifecycle outline

## MVP design choices

- Use `BindsTo=` and `After=` for each enrolled service or socket. Omit `Requisite=` to keep a single dependency responsible for pulling in the gate. Delete the owned grant flags before submitting emergency gate stops. After a close, verify the gate, members and pending jobs. Explicitly stop any still-active enrolled members, then verify again and report incomplete closure.
- A fixed udev `RUN+=` action queues a nonblocking restart of the worker on USB add/remove. Use `StartLimitIntervalSec=0` so start limiting does not suppress a later scan. Persist first absence, wait the remaining grace, then rescan. During enforcement, the internal safety timer also schedules periodic scans so a missed udev event gets another check. Choose its interval on the notebook. Only `.service` and `.socket` units can be enrolled in a policy.
- One policy owns each unit. Reject missing or ambiguous serials at enrollment. Revocation removes eligibility without grace. Another valid device in the same policy can sustain an existing grant. `on_present=start` acts only on a transition to granted.

These choices are planned and `untested` on the notebook.

## States

| State | Evidence the operator should see | Permitted behavior |
| --- | --- | --- |
| S0 installed | Installed files, no enabled monitor, owned drop-ins or live grants. Preserved configuration and snapshots may exist. | Inert. Installation performs no enable or start. |
| S1 observing | Observer enabled, zero enrolled units and zero live grants. The internal safety timer is optional in S1. Report whether it is enabled and active. | Audit changes. A prepared snapshot is inert. |
| S2 enforcing | The internal safety timer must be enabled and active throughout S2. Marked drop-ins inventory the enrolled units and agree with the applied generation and effective manager relationships. | Reconcile only enabled policies and verify outcomes. |
| DEGRADED | Expected artifacts missing, inconsistent manager state or failed integrity check. Can overlay S2 or a partial transition. | Quiesce opens, delete owned grant flags, then stop the gates and verify closure. Report unverified exposure. A missing snapshot cannot establish S0. |

**Enable.** Establish S1 first. Before arming the first policy, verify that the internal safety timer is enabled and active. If this check fails, stay in S1. Validate, stage a durable applied generation and keep its predecessor for operator inspection. Refuse orphaned enrollments or overlapping ownership. Under the shared transition lock, inspect present devices, active members and pending jobs before enabling. Require explicit --allow-stop when enabling would stop an active absent-device member. Record enough intent to resume interrupted changes. Confirm loaded effective dependencies before reporting S2.

**Disable.** Quiesce competing work for the policy. Remove only verified owned drop-ins, reload, verify detachment and pending jobs, then stop the project gate and clear its grant. If the manager cannot confirm detachment, preserve the diagnostic and pause that step. Check that the member retained its prior state. Other enabled policies remain in S2. Removing the last returns to S1. Monitor disable is allowed only after every enrollment has been detached.

**Recovery.** Keep two SSH sessions and the local console available for future human trials. Manual recovery must work without Python, the USB device or a readable snapshot. The recovery design uses marked drop-ins to inventory enrollment. Quiesce gate openers, detach verified drop-ins, reload and verify relationships, disarm gates and monitoring, then verify S0. With a failed manager, record which steps are incomplete. Reload udev after removing the owned rule. Preserve configuration, registry and snapshots. Repeat recovery from each interrupted boundary. The dead-man switch has been removed.

**Uninstall.** Require S0 or explicit recovery. Remove only confined, manifest-owned paths, leave operator data by default and keep purge a separate explicit destructive choice. Compare only the managed tree with its baseline and list retained data. All transitions, including local rescue and boot behavior, are untested.

[Português (Brasil)](../pt-BR/docs/ciclo-de-vida.md) · [Project overview](../README.md)
