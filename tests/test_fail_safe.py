import hashlib
import json
import os
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import call, patch

from usbgate import cli, demo, install, policy


def reply(unit, active="inactive", sub="dead", load="loaded", job=""):
    properties = f"Id={unit}\nLoadState={load}\nActiveState={active}\nSubState={sub}\nJob={job}\n"
    return subprocess.CompletedProcess([], 0, properties, "")


class UnitStateTests(unittest.TestCase):
    def test_service_and_timer_states(self):
        for unit, active, sub, expected in (
            (demo.SERVICE, "inactive", "dead", "inactive"),
            (demo.SERVICE, "active", "running", "active"),
            (demo.SERVICE, "activating", "start", "transitioning"),
            (demo.SERVICE, "deactivating", "stop-sigterm", "transitioning"),
            (demo.SERVICE, "failed", "failed", "failed"),
            (demo.TIMER, "active", "waiting", "active"),
        ):
            with self.subTest(active=active, sub=sub), patch.object(
                subprocess, "run", return_value=reply(unit, active, sub)
            ) as run:
                self.assertEqual(policy.unit_state(unit), expected)
                self.assertEqual(run.call_args.args[0][:2], ["/usr/bin/systemctl", "show"])
                self.assertEqual(run.call_args.args[0][-1], unit)

    def test_unknown_state_preserves_query_failure(self):
        for error in (OSError("bus unavailable"), subprocess.TimeoutExpired("systemctl", 10)):
            with self.subTest(error=error), patch.object(subprocess, "run", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "state unknown") as raised:
                    policy.unit_state(demo.SERVICE)
                self.assertIs(raised.exception.__cause__, error)
        result = reply(demo.SERVICE)
        result.returncode, result.stderr = 1, "manager unavailable"
        with patch.object(subprocess, "run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "exited 1: manager unavailable"):
                policy.unit_state(demo.SERVICE)

    def test_unusable_or_contradictory_properties(self):
        ok = reply(demo.SERVICE).stdout
        for output in ("", "inactive", "Id=presence-demo.service", ok + "ActiveState=active",
                       ok.replace(demo.SERVICE, "other.service"), ok.replace("dead", "running"),
                       ok.replace("loaded", "not-found"), ok.replace("loaded", "masked"),
                       ok.replace("inactive", "unexpected"), ok.replace("SubState=dead", "SubState="),
                       ok.replace("Job=", "Job=unexpected")):
            with self.subTest(output=output), patch.object(
                subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, "")
            ):
                with self.assertRaisesRegex(RuntimeError, "state unknown"):
                    policy.unit_state(demo.SERVICE)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for module, name, value in (
            (cli, "RUNTIME", root), (cli, "LOCK", root / "lock"), (cli, "STATE", root / "state"),
            (demo, "POLICY", root / "etc" / "demo.json"), (demo, "GRANT", root / "grant"),
            (demo, "RULE", root / "rule"), (demo, "UNIT", root / demo.SERVICE),
            (demo, "MANIFEST", root / "manifest"), (demo, "INHIBIT", root / "inhibit"),
        ):
            self.enterContext(patch.object(module, name, value))
        self.enterContext(patch.object(demo, "TRUST_UID", os.getuid()))
        self.enterContext(patch.object(demo, "TRUST_ROOT", root))
        def check_timer():
            if demo.unit_state(demo.TIMER) != "active":
                raise RuntimeError("safety monitor unavailable")
        self.enterContext(patch.object(demo, "verify_monitor", side_effect=check_timer))
        demo.RULE.touch()
        demo.UNIT.write_text("disposable test unit")
        checksum = hashlib.sha256(demo.UNIT.read_bytes()).hexdigest()
        demo.MANIFEST.write_text(json.dumps({"schema_version": 1, "files": {str(demo.UNIT): checksum}}))
        self.preflight = self.enterContext(patch.object(policy, "inspect_unit"))
        self.show = self.enterContext(patch.object(subprocess, "run"))
        self.control = self.enterContext(patch.object(demo, "systemctl"))
        self.fingerprint = "a" * 12
        self.enrollment = {"schema_version": 1, "enabled": True, "fingerprint": self.fingerprint}
        self.present = {self.fingerprint: {"assurance": "identifier-only", "classes": ["08"]}}

    def test_persistence_failure_revokes_and_confirms_stop_even_with_usb_present(self):
        for observed in ({}, self.present):
            with self.subTest(present=bool(observed)):
                demo.save_policy(self.enrollment)
                demo.GRANT.touch()
                self.show.side_effect = [reply(demo.SERVICE, "active", "running"), reply(demo.SERVICE)]
                failure = OSError("no space left")
                with patch.object(cli, "save_state", side_effect=failure), patch.object(demo, "open_grant") as grant:
                    with self.assertRaisesRegex(RuntimeError, "no space left.*grant absent.*confirmed inactive") as raised:
                        cli.observe_once(scan=lambda: observed, current_boot="test")
                self.assertIs(raised.exception.__cause__, failure)
                self.assertFalse(demo.GRANT.exists())
                grant.assert_not_called()
                self.control.assert_called_once_with("stop", demo.SERVICE)
                self.preflight.assert_called_once_with(demo.SERVICE)
                self.assertEqual(self.show.call_count, 2)
                self.control.reset_mock()
                self.preflight.reset_mock()
                self.show.reset_mock()

    def test_persistence_failure_with_no_grant_never_authorizes(self):
        demo.save_policy(self.enrollment)
        self.show.return_value = reply(demo.SERVICE)
        with patch.object(cli, "save_state", side_effect=OSError("read-only")):
            with self.assertRaisesRegex(RuntimeError, "read-only.*confirmed inactive"):
                cli.observe_once(scan=lambda: self.present, current_boot="test")
        self.assertFalse(demo.GRANT.exists())
        self.control.assert_not_called()

    def test_enable_requires_a_committed_sample(self):
        demo.save_policy(dict(self.enrollment, enabled=False))
        self.show.side_effect = [reply(demo.TIMER, "active", "waiting"),
                                 reply(demo.SERVICE), reply(demo.SERVICE)]
        with patch.object(cli, "devices", return_value=self.present), \
             patch.object(cli, "save_state", side_effect=OSError("read-only")):
            with self.assertRaisesRegex(RuntimeError, "read-only.*confirmed inactive"):
                demo.enable()
        self.control.assert_not_called()
        self.assertFalse(demo.GRANT.exists())
        self.assertFalse(demo.read_policy()["enabled"])

    def test_worker_persists_and_reconciles_through_grace(self):
        demo.save_policy(self.enrollment)
        observations = iter([self.present, {}, {}])
        clock = iter([1, 2, 12])
        self.show.side_effect = [reply(demo.TIMER, "active", "waiting"), reply(demo.SERVICE),
                                 reply(demo.SERVICE, "active", "running"),
                                 reply(demo.TIMER, "active", "waiting"),
                                 reply(demo.TIMER, "active", "waiting"),
                                 reply(demo.SERVICE, "active", "running"), reply(demo.SERVICE)]

        def wait_for_expiry(seconds):
            self.assertEqual(seconds, 10)
            self.assertTrue(demo.GRANT.is_file())
            self.assertEqual(cli.load_state()["devices"][self.fingerprint]["state"], "pending")

        with patch.object(cli.syslog, "syslog"), patch.object(cli.syslog, "openlog"):
            for _ in range(2):
                cli.observe_once(scan=observations.__next__, clock=clock.__next__,
                                 delay=wait_for_expiry, current_boot="test")
        self.assertEqual(cli.load_state()["devices"][self.fingerprint]["state"], "absent")
        self.assertFalse(demo.GRANT.exists())
        self.assertEqual(self.control.call_args_list, [call("start", demo.SERVICE), call("stop", demo.SERVICE)])

    def test_nested_persistence_revocation_and_manager_failures(self):
        demo.GRANT.touch()
        self.show.side_effect = OSError("bus unavailable")
        self.control.side_effect = subprocess.TimeoutExpired("stop", 15)
        with patch.object(cli, "save_state", side_effect=OSError("no space left")), \
             patch.object(demo, "revoke", side_effect=PermissionError("unlink denied")):
            with self.assertRaises(RuntimeError) as raised:
                cli.observe_once(scan=lambda: {}, current_boot="test")
        for detail in ("no space left", "unlink denied", "stop request failed", "timed out",
                       "bus unavailable", "inactivity unconfirmed", "recovery required"):
            self.assertIn(detail, str(raised.exception))
        self.assertTrue(demo.GRANT.exists())
        self.preflight.assert_called_once_with(demo.SERVICE)
        self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_disarmed_states_check_the_service_independently_of_the_grant(self):
        for enrolled in (False, True):
            if enrolled:
                demo.save_policy(dict(self.enrollment, enabled=False))
            for grant_present in (False, True):
                for active in (False, True):
                    with self.subTest(enrolled=enrolled, grant_present=grant_present, active=active):
                        if grant_present:
                            demo.GRANT.touch()
                        answers = [reply(demo.SERVICE)]
                        if active:
                            answers.insert(0, reply(demo.SERVICE, "active", "running"))
                        self.show.side_effect = answers
                        demo.reconcile({}, {})
                        self.assertFalse(demo.GRANT.exists())
                        self.assertEqual(self.show.call_count, len(answers))
                        if active:
                            self.control.assert_called_once_with("stop", demo.SERVICE)
                            self.preflight.assert_called_once_with(demo.SERVICE)
                        else:
                            self.control.assert_not_called()
                        self.control.reset_mock()
                        self.preflight.reset_mock()
                        self.show.reset_mock()

    def test_symlink_revocation_failure_still_stops_verified_unit(self):
        demo.GRANT.symlink_to(demo.RULE)
        self.show.side_effect = [reply(demo.SERVICE, "active", "running"), reply(demo.SERVICE)]
        with self.assertRaisesRegex(RuntimeError, "grant symlink refused.*confirmed inactive"):
            demo.reconcile({}, {})
        self.assertTrue(demo.GRANT.is_symlink())
        self.assertTrue(demo.RULE.is_file())
        self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_corrupt_policy_revokes_and_reports_incomplete_stop(self):
        demo.save_policy(self.enrollment)
        demo.POLICY.write_text("bad JSON")
        demo.GRANT.touch()
        self.show.side_effect = [reply(demo.SERVICE, "active", "running"),
                                 reply(demo.SERVICE, "deactivating", "stop")]
        with self.assertRaisesRegex(RuntimeError, "policy unreadable.*grant absent.*inactivity unconfirmed"):
            demo.reconcile({}, {})
        self.assertFalse(demo.GRANT.exists())
        self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_stop_request_error_keeps_final_confirmation(self):
        self.show.side_effect = [reply(demo.SERVICE, "active", "running"), reply(demo.SERVICE)]
        self.control.side_effect = subprocess.TimeoutExpired("stop", 15)
        with self.assertRaisesRegex(RuntimeError, "stop request failed.*confirmed inactive"):
            demo.close_demo()

    def test_incomplete_inactive_confirmation_is_reported(self):
        self.show.side_effect = [reply(demo.SERVICE, "active", "running"), reply(demo.SERVICE, load="not-found")]
        with self.assertRaisesRegex(RuntimeError, "inactivity unconfirmed.*not-found"):
            demo.close_demo()
        self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_modified_unit_is_never_stopped(self):
        demo.UNIT.write_text("changed unit")
        demo.GRANT.touch()
        self.show.return_value = reply(demo.SERVICE, "active", "running")
        with self.assertRaisesRegex(RuntimeError, "unsafe to stop.*installed file differs.*recovery required"):
            demo.reconcile({}, {})
        self.assertFalse(demo.GRANT.exists())
        self.control.assert_not_called()

    def test_enable_revokes_stale_grant_if_unit_is_unsafe(self):
        demo.save_policy(dict(self.enrollment, enabled=False))
        demo.GRANT.touch()
        demo.UNIT.write_text("changed unit")
        self.show.return_value = reply(demo.SERVICE, "active", "running")
        with self.assertRaisesRegex(RuntimeError, "installed file differs.*grant absent.*unsafe to stop"):
            demo.enable()
        self.assertFalse(demo.GRANT.exists())
        self.assertFalse(demo.read_policy()["enabled"])
        self.control.assert_not_called()

    def test_failed_open_preflight_cannot_fall_through_to_stop(self):
        demo.save_policy(self.enrollment)
        demo.GRANT.touch()
        self.show.return_value = reply(demo.SERVICE, "active", "running")
        self.preflight.side_effect = ValueError("risky relationship")
        with self.assertRaisesRegex(RuntimeError, "risky relationship.*grant absent.*unsafe to stop"):
            demo.reconcile({}, self.present)
        self.assertFalse(demo.GRANT.exists())
        self.preflight.assert_called_once_with(demo.SERVICE)
        self.control.assert_not_called()

    def test_status_reports_unknown_without_false_inactivity(self):
        self.show.side_effect = OSError("bus unavailable")
        report = demo.status()
        self.assertEqual(report["service_state"], "unknown")
        self.assertIsNone(report["service_active"])
        self.assertIn("bus unavailable", report["service_state_error"])


class LiveUninstallChecks(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(install, "SYSTEM_ROOT", self.root))
        self.enterContext(patch.object(demo, "POLICY", self.root / "policy"))
        self.enterContext(patch.object(demo, "GRANT", self.root / "grant"))
        install.install(self.root)
        self.files = [install.destination(self.root, path)
                      for path in [install.MANIFEST, *install.FILES.values()]]

    def test_all_units_must_be_confirmed_inactive(self):
        names = [cli.TIMER, cli.SERVICE, demo.SERVICE]
        with patch.object(subprocess, "run", side_effect=[reply(name) for name in names]) as run:
            install.uninstall(self.root)
        self.assertEqual([c.args[0][-1] for c in run.call_args_list], names)
        self.assertFalse(any(p.exists() for p in self.files))

    def test_refusal_preserves_entire_manifest_tree(self):
        for result in (reply(demo.SERVICE, "active", "running"),
                       reply(demo.SERVICE, "deactivating", "stop"),
                       reply(demo.SERVICE, "failed", "failed"),
                       reply(demo.SERVICE, job="42"),
                       reply(demo.SERVICE, load="not-found"),
                       subprocess.CompletedProcess([], 1, "", "manager error"),
                       subprocess.CompletedProcess([], 0, "unexpected", ""),
                       OSError("bus unavailable"), subprocess.TimeoutExpired("show", 10)):
            with self.subTest(result=result), patch.object(
                subprocess, "run", side_effect=[reply(cli.TIMER), reply(cli.SERVICE), result]
            ):
                with self.assertRaisesRegex(RuntimeError, demo.SERVICE):
                    install.uninstall(self.root)
                self.assertTrue(all(p.is_file() for p in self.files))


class LauncherTests(unittest.TestCase):
    def test_installed_launcher_uses_the_installed_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install.install(root)
            launcher = root / "usr/local/sbin/usbgate"
            unexpected = root / "usr/local/src/usbgate"
            unexpected.mkdir(parents=True)
            (unexpected / "__init__.py").touch()  # An empty, incompatible source package.
            result = subprocess.run([launcher, "--version"], check=True, text=True, capture_output=True,
                                    env={**os.environ, "PATH": "", "PYTHONPATH": str(unexpected.parent)})
            self.assertEqual(result.stdout.strip(), cli.__version__)

    def test_checkout_launcher_works_outside_the_checkout(self):
        launcher = install.PROJECT / "bin/usbgate"
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([launcher, "--help"], cwd=directory, check=True,
                                    text=True, capture_output=True)
        self.assertIn("reconcile", result.stdout)
