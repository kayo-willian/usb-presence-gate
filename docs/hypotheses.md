# Notebook checks

On 2026-11-22 the maintainer reported Debian GNU/Linux 13.8 (trixie), Python 3.13.5, systemd 257 (257.13-1~deb13u1), and kernel 6.12.117+deb13-amd64 on the test notebook.

| Check | Status | Evidence or next observation |
| --- | --- | --- |
| H1 — python3 is installed and reports version 3.13.5 | hardware-verified | Maintainer's notebook report above. |
| H1 — `tomllib` import and `CLOCK_BOOTTIME` read | hardware-verified | See the notebook transcript below. |
| USB event delivery and grace | untested | Observe add, remove, boot with the stick, rapid reconnect and removal followed by silence. |
| Service and socket closure | untested | Verify both states after removal, including explicit stop if propagation leaves a member active. |

## H1 notebook evidence

The maintainer ran this command on the test notebook on 2026-11-22.

```console
$ python3 -c 'import time, tomllib; print("tomllib OK"); print("CLOCK_BOOTTIME", time.clock_gettime(time.CLOCK_BOOTTIME))'
tomllib OK
CLOCK_BOOTTIME 44825.708116314
```

G1 and experiments S3/S4 are retired. The earlier ledger is available in Git history.
