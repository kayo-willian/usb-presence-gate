# Lifecycle outline

| State | Evidence the operator should see | Permitted behavior |
| --- | --- | --- |
| S0 installed | Installed files, no enabled monitor, owned drop-ins or live grants. Preserved configuration and snapshots may exist. | Inert. Installation performs no enable or start. |
| S1 observing | Monitor enabled, explicitly configured timer state, zero enrolled units and zero live grants. | Audit changes. A prepared snapshot is inert. |
| S2 enforcing | Persistent enrollment inventory agrees with the applied generation, owned drop-ins and effective manager relationships. | Reconcile only enabled policies and verify outcomes. |
| DEGRADED | Expected artifacts missing, inconsistent manager state or failed integrity check. Can overlay S2 or a partial transition. | Deny new grants, attempt narrowly scoped closure, report unverified exposure. A missing snapshot cannot establish S0. |

**Enable.** Establish S1 first. Validate, stage a durable applied generation and keep its predecessor for operator inspection. Refuse orphaned enrollments or overlapping ownership. Under the shared transition lock, inspect present devices, active members and pending jobs before enabling. Require explicit --allow-stop when enabling would stop an active absent-device member. Record enough intent to resume interrupted changes. Confirm loaded effective dependencies before reporting S2.

**Disable.** Quiesce competing work for the policy. Remove only verified owned drop-ins, reload, verify detachment and pending jobs, then stop the project gate and clear its grant. If the manager cannot confirm detachment, preserve the diagnostic and pause that step. Check that the member retained its prior state. Other enabled policies remain in S2. Removing the last returns to S1. Monitor disable is allowed only after every enrollment has been detached.

**Recovery.** Keep two SSH sessions and the local console available for future human trials. Manual recovery must work without Python, the USB device or a readable snapshot. The Phase 1 design should inventory project-owned artifacts, quiesce gate openers, detach verified drop-ins, reload and verify relationships, disarm gates and monitoring, then verify S0. With a failed manager, record which steps are incomplete. Removing a rule file can leave the loaded rule in effect until udev reloads. Preserve configuration, registry and snapshots. Repeat recovery from each interrupted boundary. The dead-man switch has been removed.

**Uninstall.** Require S0 or explicit recovery. Remove only confined, manifest-owned paths, leave operator data by default and keep purge a separate explicit destructive choice. Verify the baseline with preserved data accounted for. All transitions, including local rescue and boot behavior, are untested.
