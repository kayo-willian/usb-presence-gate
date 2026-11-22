# S1-lite — service and socket gate

Run these trials on the target host only when the operator is ready. Use two SSH sessions and keep the local console available. The only members are a sleeping fixture service and a root-only local Unix socket. Their relationship to the gate is the variable under test. No fixture is enabled at boot. Use root for the commands below, from this directory. Run each block separately and record unexpected outcomes before proceeding.

## Gate ordering in this experiment

A local static check with the default gate dependencies found an ordering cycle through basic.target, sockets.target, the member socket and the gate. Both variants below use the same candidate adjustment on the **fixture gate**: disable its default dependencies, order it after sysinit.target, and restore shutdown ordering explicitly. The member socket retains its normal dependencies. Verify this candidate in the system manager on the notebook. Record any ordering-cycle diagnostic and stop that trial. This fixture choice does not settle G1.

## Stage the three units in /run

First inspect the three names with `systemctl cat usbgate-s1-lite-gate.service usbgate-s1-lite-member.service usbgate-s1-lite-member.socket`. On a fresh trial the manager should find none. Inspect /run/usbgate-s1-lite and the three corresponding paths and member drop-in directories in /run/systemd/system. If any exist, resolve their ownership before staging anything. Keep the starting SSH and network observations for comparison.

```sh
install -d -m 0700 /run/usbgate-s1-lite
install -m 0644 usbgate-s1-lite-gate.service usbgate-s1-lite-member.service usbgate-s1-lite-member.socket /run/systemd/system/
systemd-analyze verify /run/systemd/system/usbgate-s1-lite-gate.service /run/systemd/system/usbgate-s1-lite-member.service /run/systemd/system/usbgate-s1-lite-member.socket
systemctl daemon-reload
```

Use this readout after **each** action below, even when the job returns a nonzero status. Record the job's exit code immediately with `echo "$?"`. A condition-skipped job may return success. Check actual state and the listener.

```sh
systemctl show usbgate-s1-lite-gate.service usbgate-s1-lite-member.service usbgate-s1-lite-member.socket -p Id -p LoadState -p ActiveState -p SubState -p ConditionResult -p Result -p Job -p BindsTo -p After -p Requisite -p DropInPaths
ss -xl | grep -F /run/usbgate-s1-lite/probe.sock
```

## Run the same matrix twice

Run variant A with the shipped BindsTo and After. With the gate and members initially inactive and the flag absent, perform the following steps. If any closed-state attempt leaves a member active or a listener reachable, record the failure, stop the three fixtures explicitly, and restore the row's initial state before the next trial.

| Step | Operator action | Observable criterion |
| --- | --- | --- |
| 1 | Start `usbgate-s1-lite-member.service` directly with systemctl. Then independently try `systemctl start usbgate-s1-lite-member.socket`. | With the flag absent, neither attempt leaves an active member or listening socket. Record failed or skipped jobs separately. |
| 2 | Create the flag with `install -m 0600 /dev/null /run/usbgate-s1-lite/ok`. Try the direct service start again with the gate initially inactive. | Record whether the dependency transaction starts the gate and the member. |
| 3 | Stop the fixture service, socket and gate. Keep the flag. Run `systemctl start usbgate-s1-lite-gate.service` and then `systemctl start usbgate-s1-lite-member.socket`. Use the connection probe below once. | Observe listening socket, then active service after connection. |
| 4 | Remove the flag with `rm -f /run/usbgate-s1-lite/ok`. Read state before issuing `systemctl stop usbgate-s1-lite-gate.service`. Read state again. | Distinguish flag removal from stop propagation. After the stop, both members should be inactive and the listener gone. |
| 5 | Retry the direct service and socket starts separately with the flag absent. Attempt the connection probe again. | No active member or successful connection. Any reopening fails this variant. |

The probe connects locally and exits without sending any data.

```sh
python3 -c 'import socket; s = socket.socket(socket.AF_UNIX); s.connect("/run/usbgate-s1-lite/probe.sock"); s.close()'
```

For variant B, first remove the flag and stop all three fixtures. Then install the additional relationship on both members. Repeat steps 1–5 and capture the same properties, including the effective Requisite list. If a variant only works with an explicitly started gate, record that distinction.

```sh
install -d -m 0755 /run/systemd/system/usbgate-s1-lite-member.service.d /run/systemd/system/usbgate-s1-lite-member.socket.d
install -m 0644 requisite.conf /run/systemd/system/usbgate-s1-lite-member.service.d/50-requisite.conf
install -m 0644 requisite.conf /run/systemd/system/usbgate-s1-lite-member.socket.d/50-requisite.conf
systemd-analyze verify /run/systemd/system/usbgate-s1-lite-gate.service /run/systemd/system/usbgate-s1-lite-member.service /run/systemd/system/usbgate-s1-lite-member.socket
systemctl daemon-reload
```

## Remove the fixture

Remove only files identified as this trial's in the initial inspection. Omit the two drop-in directories from the rmdir command if variant B was never staged.

```sh
rm -f /run/usbgate-s1-lite/ok
systemctl stop usbgate-s1-lite-member.socket usbgate-s1-lite-member.service usbgate-s1-lite-gate.service
rm -f /run/systemd/system/usbgate-s1-lite-member.service.d/50-requisite.conf /run/systemd/system/usbgate-s1-lite-member.socket.d/50-requisite.conf
rmdir /run/systemd/system/usbgate-s1-lite-member.service.d /run/systemd/system/usbgate-s1-lite-member.socket.d
rm -f /run/systemd/system/usbgate-s1-lite-gate.service /run/systemd/system/usbgate-s1-lite-member.service /run/systemd/system/usbgate-s1-lite-member.socket
rmdir /run/usbgate-s1-lite
systemctl daemon-reload
```

Verify the listener is gone, both SSH sessions and the console remain usable, and the three manager names have no installed fragment. For each row supply date, exact commands, exit codes, redacted output, kernel, systemd version and device context (S1-lite uses no USB device). Status on the target host is `untested`.
