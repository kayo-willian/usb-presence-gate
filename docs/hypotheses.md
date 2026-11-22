# Hypothesis ledger

All behavioral entries start as `untested`. “Retired” describes scope, not a test result. Hardware evidence must come from the human running the target notebook. H13 instead needs the actual CI run.

| ID | Question | Evidence needed | Status |
| --- | --- | --- | --- |
| H1 | Is a suitable Python 3 available? | Interpreter/package version and stdlib imports including tomllib and the boot clock API. | untested |
| H2 | Does the intended stick have a usable serial and stable class set? | Redacted observations across reconnects, plus ambiguity and missing-serial cases. | untested |
| H3 | Are add, remove and coldplug events delivered? | S2 event timeline and final scans. | untested |
| H4 | Can udev submit the fixed restart under its sandbox? | S2 worker, journal and manager job observations. | untested |
| H5 | Are both boot enumeration orders safe? | S1/S2 records with the device present and absent, including first gate decision and SSH/network state. | untested |
| H6 | How do disconnects and grace interact? | Timed removal, transient disconnect, reinsertion and single-event grace expiry. | untested |
| H7 | Is journal storage persistent and bounded? | Journal configuration, disk usage across a burst and retention across a normal boot. | untested |
| H8 | What does a completed scan cost on the Atom? | CPU, peak RSS, elapsed time, completion rate and SSH responsiveness, idle and during a burst. | untested |
| H9 | Does incremental hardening permit necessary reads, writes and bus calls? | Per-directive positive and negative checks plus systemd-analyze security output. | untested |
| H10 | Does the conditioned gate enforce BindsTo with After? | S1 start, stop and boot matrix across all four unit types. | untested |
| H11 | What happens across lid closure or resume? | logind policy and post-resume rescan, deadline and SSH observations. | untested |
| H12 | Are interface classes stable with uas and usb-storage? | Redacted active-configuration class sets with the observed drivers. Record unavailable variants as untested. | untested |
| H13 | Can the runner validate units and rules? | CI tool versions, invocations and results for systemd-analyze verify and udevadm verify. | untested |
| H14 | Does the host avoid automatic mounting? | Passive mount and service observations on insertion. Keep media contents untouched. | untested |
| H15 | Is manual recovery possible via console or rescue? | Human recovery transcript, including CLI-unavailable case and preserved access. Rescue requires its own approved session. | untested |
| H16 | Can restarts starve reconciliation with start limiting disabled? | S2 counts of events, starts, cancellations, completions and time to verified final state. | untested |
| H17 | What can glob stop and OnFailure contain? | S4 exact instances, flags, jobs, manager outcomes and later activation attempts. | untested |
| H18 | How does Requisite compose with BindsTo and boot ordering? | Both S1 variants including skipped conditions, jobs and failed-unit noise. | untested |
| H19 | Is the tag/device-unit fallback viable? | S2 tags, escaped instance identity, device lifecycle and observed removal callback. | untested |
| H20 | Does interface enumeration agree with bNumInterfaces? | Partial-to-complete scans, including disappearing entries and repeated class codes. | untested |
| H21 | Which effective properties and formats exist per unit type? | S1/S3 redacted raw systemctl show output with version, aliases, triggers, propagation, conflicts, jobs and timeouts. | untested |
| H22 | Dead-man switch via systemd-run | Retired by final MVP decision. No experiment or implementation planned. | untested |
