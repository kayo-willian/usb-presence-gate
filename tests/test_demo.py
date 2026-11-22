import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from usbgate import cli, demo


class DemoPolicyTests(unittest.TestCase):
    def test_identity_requires_unique_serial_storage(self):
        policy = {"fingerprint": "a" * 12}
        valid = {"a" * 12: {"assurance": "identifier-only", "classes": ["08"]}}
        self.assertTrue(demo.key_present(policy, valid))
        for other in (
            {}, {"a" * 12: {"assurance": "ambiguous", "classes": ["08"]}},
            {"a" * 12: {"assurance": "weak", "classes": ["08"]}},
            {"a" * 12: {"assurance": "identifier-only", "classes": ["03"]}},
        ):
            with self.subTest(other=other):
                self.assertFalse(demo.key_present(policy, other))

    def test_policy_roundtrip_is_private(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "policy" / "demo.json"
            with patch.object(demo, "POLICY", p):
                self.assertIsNone(demo.read_policy())
                demo.save_policy({"schema_version": 1, "fingerprint": "a" * 12,
                                  "enabled": False})
                self.assertEqual(demo.read_policy()["fingerprint"], "a" * 12)
                self.assertEqual(p.stat().st_mode & 0o077, 0)

    def test_corrupt_policy_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "policy" / "demo.json"
            with patch.object(demo, "POLICY", p):
                demo.save_policy({"schema_version": 1, "fingerprint": "a" * 12,
                                  "enabled": False})
                p.write_text("this is not JSON")
                with self.assertRaisesRegex(RuntimeError, "unreadable"):
                    demo.read_policy()

    def test_policy_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original"
            original.write_text("data")
            symlink = Path(directory) / "link"
            symlink.symlink_to(original)
            with patch.object(demo, "POLICY", symlink):
                with self.assertRaisesRegex(RuntimeError, "symlink"):
                    demo.read_policy()
                with self.assertRaisesRegex(RuntimeError, "symlink"):
                    demo.save_policy({"schema_version": 1, "fingerprint": "a" * 12,
                                      "enabled": False})
            self.assertEqual(original.read_text(), "data")

    def test_enroll_rejects_weak_identity(self):
        with patch.object(demo, "read_policy", return_value=None), \
             patch.object(cli, "devices", return_value={
                 "a" * 12: {"assurance": "weak", "classes": ["08"]}}), \
             patch.object(demo, "save_policy") as writer:
            with self.assertRaisesRegex(ValueError, "unambiguous"):
                demo.enroll("a" * 12)
            writer.assert_not_called()

    def test_enroll_saves_disabled_policy(self):
        with patch.object(demo, "read_policy", return_value=None), \
             patch.object(cli, "devices", return_value={
                 "a" * 12: {"assurance": "identifier-only", "classes": ["08"]}}), \
             patch.object(demo, "save_policy") as writer:
            demo.enroll("a" * 12)
            self.assertFalse(writer.call_args.args[0]["enabled"])

    def test_monitor_disable_refuses_active_demo(self):
        with patch.object(cli.os, "geteuid", return_value=0), \
             patch.object(cli, "SOURCE_RULE", Path("/pretend/install/packaging/udev/70-usbgate.rules")), \
             patch.object(demo, "read_policy", return_value={"enabled": True}), \
             patch.object(cli, "has_enrollment", return_value=False), \
             patch.object(cli.subprocess, "run") as shell:
            # Bypass the installed-path check with a real temporary file below.
            with tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "rule"
                source.write_text("test")
                with patch.object(cli, "SOURCE_RULE", source):
                    with self.assertRaisesRegex(RuntimeError, "disable the demo"):
                        cli.monitor(False)
            shell.assert_not_called()


class DemoReconciliationTests(unittest.TestCase):
    @staticmethod
    def policy():
        return {"schema_version": 1, "fingerprint": "a" * 12, "enabled": True}

    @staticmethod
    def observations():
        return {"a" * 12: {"assurance": "identifier-only", "classes": ["08"]}}

    @staticmethod
    def state(status):
        return {"devices": {"a" * 12: {"state": status}}}

    def test_present_opens_once_and_absent_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            grant = Path(directory) / "run" / "demo-grant"
            rule = Path(directory) / "rule"
            rule.write_text("rule")
            running = [False]
            calls = []
            def fake_systemctl(*args, **kwargs):
                calls.append(args[0])
                if args[0] == "start":
                    running[0] = True
                if args[0] == "stop":
                    running[0] = False
            with patch.object(demo, "POLICY", Path(directory) / "dummy"), \
                 patch.object(demo, "GRANT", grant), \
                 patch.object(demo, "RULE", rule), \
                 patch.object(demo, "read_policy", return_value=self.policy()), \
                 patch.object(demo, "verify_unit"), \
                 patch.object(demo, "timer_active", return_value=True), \
                 patch.object(demo, "systemctl", side_effect=fake_systemctl), \
                 patch.object(demo, "service_active", side_effect=lambda: running[0]):
                demo.reconcile(self.state("present"), self.observations())
                self.assertTrue(grant.is_file())
                self.assertTrue(running[0])
                demo.reconcile(self.state("present"), self.observations())
                self.assertEqual(calls.count("start"), 1)
                demo.reconcile(self.state("pending"), {})
                self.assertTrue(grant.is_file())
                self.assertTrue(running[0])
                demo.reconcile(self.state("absent"), {})
                self.assertFalse(grant.exists())
                self.assertFalse(running[0])
                self.assertEqual(calls.count("stop"), 1)

    def test_timer_failure_closes_demo(self):
        with tempfile.TemporaryDirectory() as directory:
            grant = Path(directory) / "demo-grant"
            grant.write_text("")
            rule = Path(directory) / "rule"
            rule.write_text("")
            with patch.object(demo, "GRANT", grant), \
                 patch.object(demo, "RULE", rule), \
                 patch.object(demo, "read_policy", return_value=self.policy()), \
                 patch.object(demo, "verify_unit"), \
                 patch.object(demo, "timer_active", return_value=False), \
                 patch.object(demo, "stop_demo") as stopper:
                with self.assertRaisesRegex(RuntimeError, "safety monitor unavailable"):
                    demo.reconcile(self.state("present"), self.observations())
                self.assertFalse(grant.exists())
                stopper.assert_called_once()

    def test_corrupt_policy_closes_demo(self):
        with patch.object(demo, "read_policy", side_effect=RuntimeError("corrupt")), \
             patch.object(demo, "close_demo") as close:
            with self.assertRaisesRegex(RuntimeError, "corrupt"):
                demo.reconcile({}, {})
            close.assert_called_once()

    def test_ambiguous_identity_closes_even_if_observation_present(self):
        with tempfile.TemporaryDirectory() as directory:
            rule = Path(directory) / "rule"
            rule.write_text("rule")
            with patch.object(demo, "RULE", rule), \
                 patch.object(demo, "read_policy", return_value=self.policy()), \
                 patch.object(demo, "verify_unit"), \
                 patch.object(demo, "timer_active", return_value=True), \
                 patch.object(demo, "close_demo") as closer:
                demo.reconcile(self.state("present"), {
                    "a" * 12: {"assurance": "ambiguous", "classes": ["08"]}})
                closer.assert_called_once()


    def test_disable_stops_before_disarming(self):
        policy = self.policy()
        events = []
        with patch.object(demo, "read_policy", return_value=policy), \
             patch.object(demo, "close_demo", side_effect=lambda: events.append("stop")), \
             patch.object(demo, "save_policy", side_effect=lambda p: events.append(("save", p["enabled"]))):
            demo.disable()
        self.assertEqual(events, ["stop", ("save", False)])

    def test_enable_refuses_inactive_safety_timer(self):
        with patch.object(demo, "read_policy", return_value=dict(self.policy(), enabled=False)), \
             patch.object(demo, "verify_unit"), \
             patch.object(demo, "RULE", Path("/temporary/fictional/missing/rule")), \
             patch.object(demo, "timer_active", return_value=False), \
             patch.object(demo, "save_policy") as writer:
            with self.assertRaises(RuntimeError):
                demo.enable()
            writer.assert_not_called()


class DemoStartFailureTests(unittest.TestCase):
    def test_failed_start_retries_closure(self):
        import subprocess
        policy = {"schema_version": 1, "fingerprint": "a" * 12, "enabled": True}
        state = {"devices": {"a" * 12: {"state": "present"}}}
        observations = {"a" * 12: {"assurance": "identifier-only", "classes": ["08"]}}
        with tempfile.TemporaryDirectory() as directory:
            rule = Path(directory) / "rule"
            rule.write_text("dummy")
            with patch.object(demo, "RULE", rule), \
                 patch.object(demo, "read_policy", return_value=policy), \
                 patch.object(demo, "verify_unit"), \
                 patch.object(demo, "timer_active", return_value=True), \
                 patch.object(demo, "open_grant", return_value=True), \
                 patch.object(demo, "systemctl", side_effect=subprocess.CalledProcessError(1, "systemctl start")), \
                 patch.object(demo, "close_demo") as closer:
                with self.assertRaises(subprocess.CalledProcessError):
                    demo.reconcile(state, observations)
                closer.assert_called_once()

    def test_pending_clone_does_not_keep_existing_grant(self):
        policy = {"schema_version": 1, "fingerprint": "a" * 12, "enabled": True}
        state = {"devices": {"a" * 12: {"state": "pending"}}}
        observations = {"a" * 12: {"assurance": "ambiguous", "classes": ["08"]}}
        with tempfile.TemporaryDirectory() as directory:
            grant = Path(directory) / "demo-grant"
            rule = Path(directory) / "rule"
            grant.write_text("")
            rule.write_text("dummy")
            with patch.object(demo, "GRANT", grant), \
                 patch.object(demo, "RULE", rule), \
                 patch.object(demo, "read_policy", return_value=policy), \
                 patch.object(demo, "verify_unit"), \
                 patch.object(demo, "timer_active", return_value=True), \
                 patch.object(demo, "stop_demo") as stopper:
                demo.reconcile(state, observations)
                self.assertFalse(grant.exists())
                stopper.assert_called_once()
