# usb-presence-gate

A small lab tool for headless Debian 13. The planned physical-presence interlock allows an enrolled, noncritical systemd service or socket to run while a registered USB device is present. USB descriptors provide identifier-only assurance and can be cloned. Each unit belongs to one policy. Enrollment rejects devices with missing or ambiguous serials.

## Before the first test

- [ ] Open two independent SSH sessions to the notebook and confirm both respond.
- [ ] Keep the local keyboard and display within reach and confirm you can use the console.
- [ ] For a future gate test, choose a disposable service and socket that have no critical dependencies.

## Operations

This documentation step provides a read-only notebook check. The CLI, installer and recovery procedure are planned. Exact commands will accompany each implemented operation.

### Install

Copy the tool and record the installed files. **Status:** not implemented yet.

### Setup

Check the host and turn on observation. **Status:** not implemented yet.

### Enroll

Register a USB device with an unambiguous identifier. **Status:** not implemented yet.

### Enable

Apply a policy to a noncritical service or socket. **Status:** not implemented yet.

### Test

Exercise insertion and removal with a disposable unit. **Status:** not implemented yet.

### Status

Read the monitor and gate state. **Status:** not implemented yet.

### Disable

Detach the policy and return the unit to operator control. **Status:** not implemented yet.

### Recover

Restore an inert installation without the CLI or USB device. **Status:** not implemented yet.

### Uninstall

Remove manifest-owned files and list retained data. **Status:** not implemented yet.

## Read-only notebook check

**Command status: hardware-verified.** On 2026-11-22 the maintainer confirmed that Python 3.13.5 on the test notebook imported `tomllib` and read `CLOCK_BOOTTIME`.

```sh
python3 -c 'import time, tomllib; print("tomllib OK"); print("CLOCK_BOOTTIME", time.clock_gettime(time.CLOCK_BOOTTIME))'
```

The maintainer has already reported Python 3.13.5 on the notebook. [Hardware evidence](docs/hypotheses.md)

## Credits

Henrique (rique-decoder) https://github.com/rique-decoder inspired this project with linux-usb-security-token. USBGuard is a related approach to device authorization. [Prior art](docs/prior-art.md)

AI assisted with documentation and spike preparation. The maintainer reviews changes and supplies target-notebook results.
