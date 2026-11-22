# Notebook checks

On 2026-11-22 the maintainer reported Debian GNU/Linux 13.8 (trixie), Python 3.13.5, systemd 257 (257.13-1~deb13u1), and kernel 6.12.117+deb13-amd64 on the test notebook.

| Check | Status | Evidence or next observation |
| --- | --- | --- |
| H1 — python3 is installed and reports version 3.13.5 | hardware-verified | Maintainer's notebook report above. |
| H1 — tomllib import and CLOCK_BOOTTIME read | untested | Run the read-only check in the [README](../README.md). |
| USB event delivery and grace | untested | Observe add, remove, boot with the stick, rapid reconnect and removal followed by silence. |
| Service and socket closure | untested | Verify both states after removal, including explicit stop if propagation leaves a member active. |

G1 and experiments S3/S4 are retired. The earlier ledger is available in Git history.
