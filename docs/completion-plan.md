# Milestone completed; future scope

**Status on 2026-11-22: experimental demo milestone completed, development paused.**

This repository has two implemented capabilities:

- A lightweight, physically tested **USB presence observer**.
- An opt-in, physically tested **gate for one fixed project-owned disposable
  `presence-demo.service`**. It starts and stops this idle unit according
  to reported USB presence, with a detection-relative grace period.

The initial repository planning documents explored a generic gate for
selected noncritical services/sockets. **That plan was deliberately reduced
for this milestone** to avoid placing infrastructure at risk. The current
implementation does not register arbitrary existing services, does not
manage sockets, and has no real hardware authentication.

## Physical acceptance record

The maintainer reported on Debian 13:

- 41 automated tests passed and `systemd-analyze verify` emitted no warnings.
- USB scanning, observation, inert installation, enrollment, explicit arm
  and physical USB unplug/replug were successful.
- The disposable unit stopped after a processed removal and restarted
  after reconnect. A normal manual start without the demo grant did not
  start it.
- A reboot with the stick inserted restored the demo, timer and SSH.
- Recovery without Python revoked the grant, stopped the demo and
  disabled observation; the source-based uninstall removed managed files.

These are reproducible **lab observations**, not certification of security,
a timed guarantee, or evidence for arbitrary services.

## Unimplemented or only partially verified

- Arbitrary service and socket enrollment, multiple policies and full
  dependency/activation-path enforcement.
- Cryptographic token authentication, protection from USB descriptor
  spoofing or theft, and secure USB filesystem secrets.
- Hardware verification of rapid replug inside the grace interval,
  timer-only event processing, corrupt-policy recovery, unplugged boot,
  USB identifier cloning and severe host/manager failures.
- A hard maximum interval from physical unplug to confirmed process stop,
  security assurance or production support.

## Possible expansions, not commitments

Future maintainers could investigate a generic noncritical service gate,
stronger integration checks, measured fallback timing, more failure
injection or hardware-backed challenge/response. Each would need a new
architecture review, a feature branch, independent tests, real hardware
validation, and a recovery plan. No new feature is scheduled.

Refer to [the complete README](../README.md), [the demo safety record](demo-safety.md),
[recovery](recovery.md) and [the extension guide](extending.md).

Never use the demonstration to block SSH, authentication, networking,
firewall, Docker engine or other critical infrastructure.

[Português (Brasil)](../pt-BR/docs/plano-de-conclusao.md) · [Project overview](../README.md)
