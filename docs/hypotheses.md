# Notebook checks

On 2026-11-22 the maintainer reported Debian GNU/Linux 13.8 (trixie), Python 3.13.5, systemd 257 (257.13-1~deb13u1), and kernel 6.12.117+deb13-amd64 on the test notebook.

| Check | Status | Evidence or next observation |
| --- | --- | --- |
| H1 — python3 is installed and reports version 3.13.5 | hardware-verified | Maintainer's notebook report above. |
| H1 — `tomllib` import and `CLOCK_BOOTTIME` read | hardware-verified | See the notebook transcript below. |
| USB observation, removal and grace | hardware-verified | Maintainer observed the device as present, absence pending, absent after 10 seconds, and returned; journald confirmed the transitions. Trigger isolation not yet measured. |
| Reboot with the USB already connected | hardware-verified | After a physical reboot, the demo service and timer returned active with the USB still connected and SSH remained available. |\n| Rapid reconnection within the 10-second grace | untested | Requires a separate physical timing test; not inferred from a later reconnect. |
| Bundled disposable `presence-demo.service` closure | hardware-verified | Physical USB removal stopped the bundled demo after observation; a normal manual start with grant absent left it inactive. |\n| Arbitrary service/socket closure | not implemented | The CLI has no general enrollment or socket enforcement. |

## H1 notebook evidence

The maintainer ran this command on the test notebook on 2026-11-22.

```console
$ python3 -c 'import time, tomllib; print("tomllib OK"); print("CLOCK_BOOTTIME", time.clock_gettime(time.CLOCK_BOOTTIME))'
tomllib OK
CLOCK_BOOTTIME 44825.708116314
```

G1 and experiments S3/S4 are retired. The earlier ledger is available in Git history.
