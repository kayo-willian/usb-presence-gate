# S2-lite — USB delivery and grace expiry

This oneshot observes occupancy of one operator-selected USB port. Its only outputs are journal messages and a boot-local absence timestamp. The udev rule submits a fixed restart on USB device add/remove. No USB descriptor is read, and the worker has no systemctl calls. Use the same stick, port and hub arrangement throughout. A different device in that port produces the same observation.

The five-second grace is a fixture value. The worker stores first observed absence on CLOCK_BOOTTIME, waits the remaining interval and rescans before reporting the outcome. An observed return clears the marker. Every event can restart the worker, including events from other ports. A new invocation can inherit the deadline. The observer deliberately has no timer so that the silence case measures the worker itself. Future lifecycle S2 enforcement requires a running timer.

## Prepare on the target

Use two SSH sessions and have the local console available. Work as root from this directory. Record date, kernel, systemd and udev versions, SSH/network state and a fictional label for the test stick. Keep the USB media unmounted. Inspect the candidate unit with `systemctl cat usbgate-s2-lite-observe.service`. Check /etc/usbgate-s2-lite, /run/usbgate-s2-lite, the unit destination, any unit drop-ins and the rule filename in the udev rules search paths. Resolve collisions before installing. The fixture persists across a normal boot so the operator can inspect coldplug.

Find the kernel port location by comparing the output of the following command with the device connected and disconnected. Choose the device entry that appears on connection. A location such as `1-2.3` is fictional. Entries containing a colon identify interfaces. Use the actual location only in the host-local configuration. Leave the stick disconnected before the add trial.

```sh
ls -1 /sys/bus/usb/devices
```

Stage the worker and unit first. At the read prompt enter just the numeric port location. Check the effective FragmentPath and DropInPaths before loading the udev rule.

```sh
install -d -m 0700 /etc/usbgate-s2-lite
install -m 0600 observe.py /etc/usbgate-s2-lite/observe.py
read -r spike_port
printf 'SPIKE_PORT=%s\n' "$spike_port" > /etc/usbgate-s2-lite/port.conf
chmod 0600 /etc/usbgate-s2-lite/port.conf
systemd-analyze verify usbgate-s2-lite-observe.service
udevadm verify 70-usbgate-s2-lite.rules
install -m 0644 usbgate-s2-lite-observe.service /etc/systemd/system/
systemctl daemon-reload
systemctl show usbgate-s2-lite-observe.service -p FragmentPath -p DropInPaths
install -m 0644 70-usbgate-s2-lite.rules /etc/udev/rules.d/
udevadm control --reload
```

In one session watch udev with `udevadm monitor --udev --subsystem-match=usb/usb_device`. In the other, use `journalctl -b -f -n 0 -o short-monotonic -u usbgate-s2-lite-observe.service`. Capture the event direction, worker begin and complete records and boot-relative times. Keep raw paths local and redact identifiers in shared evidence. Use the sysfs listing as an independent final-state check. The observer unit can be inactive after a successful oneshot.

## Trial matrix

| Case | Physical action | Evidence to capture |
| --- | --- | --- |
| Add | Insert the stick in the empty selected port. | udev add, a worker begin and complete with present=1, and occupancy in sysfs. |
| Remove | From verified presence, unplug the stick. | udev remove, first absent record with since_ns and deadline_ns, then the completion and final sysfs listing. |
| Boot with stick | Leave the stick in the selected port during a separately authorized normal boot. Inspect the current boot journal before touching the device. | An observer invocation and complete with present=1 in the new boot, before any manual start, plus matching sysfs occupancy and restored SSH/network. Record missing coldplug, changed bus numbering or a mount as a deviation. |
| Rapid reconnect | Start present, unplug, and reinsert during the five-second grace. | Both physical events, any worker cancellation, the next begin and final complete with present=1. Check that /run/usbgate-s2-lite/absent_since is absent. If the first scan never observed absence, record coalescing and repeat after seeing the absent line to exercise interrupted grace. |
| Remove then silence | Establish present=1, unplug once, and leave all USB ports untouched for longer than five seconds. Do not start the worker manually. | A single absence episode, no later udev event, then complete with rescan=1 and present=0. Its boot_ns must reach the recorded deadline. Record a missing completion or extra event explicitly. |

If an ordinary boot is unavailable, leave that row untested and record it later. For boot evidence use `journalctl -b -o short-monotonic -u usbgate-s2-lite-observe.service`. For timing use the worker's boot_ns fields within one boot. Different boot epochs cannot be compared. Record actual elapsed time, resulting jobs and deviations. A delivered event without a completed scan remains an unresolved case.

## Cleanup

Stop the journal and udev viewers with Ctrl-C. Remove the fixture rule first, reload and drain pending udev events before stopping the worker. Remove only this trial's files. A fresh run should start with an empty runtime directory.

```sh
rm -f /etc/udev/rules.d/70-usbgate-s2-lite.rules
udevadm control --reload
udevadm settle
systemctl stop usbgate-s2-lite-observe.service
rm -f /etc/systemd/system/usbgate-s2-lite-observe.service
systemctl daemon-reload
rm -f /etc/usbgate-s2-lite/observe.py /etc/usbgate-s2-lite/port.conf
rmdir /etc/usbgate-s2-lite
rm -f /run/usbgate-s2-lite/absent_since /run/usbgate-s2-lite/absent_since.next
```

If the runtime directory exists, remove it with `rmdir /run/usbgate-s2-lite`. Verify that the unit and rule are absent, SSH/network and the local console are usable, and no new worker appears after a physical add/remove. Paste the date, exact commands, redacted output, kernel, fictional device label and observed result for each row. Target status is `untested`.
