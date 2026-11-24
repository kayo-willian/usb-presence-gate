"""Administrative transitions on temporary files and a simulated service manager."""
from contextlib import contextmanager
import fcntl
import multiprocessing
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from usbgate import cli, demo


class AdminFixture(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = root
        for module, name, path in (
            (cli, "RUNTIME", root / "run"), (cli, "LOCK", root / "run/lock"),
            (cli, "STATE", root / "run/state"), (cli, "SOURCE_RULE", root / "source"),
            (cli, "RULE", root / "rule"), (demo, "RULE", root / "rule"),
            (demo, "INHIBIT", root / "inhibit"), (demo, "POLICY", root / "etc/demo.json"),
            (demo, "GRANT", root / "run/grant"),
        ):
            self.enterContext(patch.object(module, name, path))
        cli.RUNTIME.mkdir(mode=0o700)
        cli.SOURCE_RULE.write_text("test rule")
        cli.RULE.write_bytes(cli.SOURCE_RULE.read_bytes())
        self.enterContext(patch.object(demo, "TRUST_UID", os.getuid()))
        self.enterContext(patch.object(demo, "TRUST_ROOT", root))
        self.enterContext(patch.object(demo, "installed_bytes", side_effect=lambda path: path.read_bytes()))
        self.enterContext(patch.object(demo, "verify_timer", side_effect=self.check_timer))
        self.timer = root / "timer"
        self.service = root / "service"
        self.timer.write_text("active")
        self.service.write_text("inactive")
        self.policy = {"schema_version": 1, "fingerprint": "a" * 12, "enabled": False}
        self.present = {self.policy["fingerprint"]: {"assurance": "identifier-only", "classes": ["08"]}}
        demo.save_policy(self.policy)
        self.enterContext(patch.object(cli, "devices", return_value=self.present))
        self.enterContext(patch.object(cli, "has_enrollment", return_value=False))
        self.enterContext(patch.object(demo, "require_root"))
        self.enterContext(patch.object(cli.syslog, "syslog"))
        self.enterContext(patch.object(cli.syslog, "openlog"))
        self.verify = self.enterContext(patch.object(demo, "verify_unit"))
        self.control = self.enterContext(patch.object(demo, "systemctl", side_effect=self.actuate))
        self.enterContext(patch.object(cli, "unit_state", side_effect=self.state))
        self.show = self.enterContext(patch.object(demo, "unit_state", side_effect=self.state))
        self.enterContext(patch.object(subprocess, "run", side_effect=self.configure))

    def check_timer(self, *, expected_state="enabled"):
        if expected_state == "enabled" and self.state(cli.TIMER) != "active":
            raise RuntimeError("timer inactive")

    def state(self, name):
        if name == demo.SERVICE:
            return self.service.read_text()
        if name == cli.TIMER:
            return self.timer.read_text()
        self.assertEqual(name, cli.SERVICE)
        return "inactive"

    def actuate(self, verb, unit):
        self.assertEqual(unit, demo.SERVICE)
        self.assertIn(verb, ("start", "stop"))
        if verb == "start":
            self.assertTrue(demo.GRANT.is_file())
            self.assertFalse(demo.inhibited())
        self.service.write_text("active" if verb == "start" else "inactive")

    def configure(self, args, **kwargs):
        if args[1] in ("disable", "enable"):
            self.assertEqual(args[-1], cli.TIMER)
            self.timer.write_text("active" if args[1] == "enable" else "inactive")

    def monitor(self, enable):
        cli.monitor(enable)

    def worker(self):
        return cli.observe_once(current_boot="test", grace=0)

    def arm(self):
        demo.lock_and_run(demo.enable)

    def disable(self):
        demo.lock_and_run(demo.disable)

    def assert_closed(self):
        self.assertFalse(demo.GRANT.exists())
        self.assertEqual(self.service.read_text(), "inactive")


class ActivationTests(AdminFixture):
    def test_manual_stop_and_interrupted_start_converge(self):
        self.arm()
        for has_grant in (True, False):
            with self.subTest(has_grant=has_grant):
                self.service.write_text("inactive")
                if not has_grant:
                    demo.GRANT.unlink()
                self.control.reset_mock()
                self.worker()
                self.control.assert_called_once_with("start", demo.SERVICE)
                self.assertEqual(self.service.read_text(), "active")
                self.worker()
                self.control.assert_called_once()

    def test_uncertain_or_failed_state_never_starts(self):
        self.arm()
        for state in ("transitioning", "failed", "unknown"):
            with self.subTest(state=state):
                self.service.write_text(state)
                demo.GRANT.touch()
                self.control.reset_mock()
                def query(unit):
                    if unit == demo.SERVICE and self.service.read_text() == "unknown":
                        raise RuntimeError("state unknown")
                    return self.state(unit)
                self.show.side_effect = query
                with self.assertRaisesRegex(RuntimeError, "start unsafe|state unknown"):
                    self.worker()
                self.assert_closed()
                self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_interrupted_start_with_invalid_observation(self):
        self.arm()
        self.service.write_text("inactive")
        self.control.reset_mock()
        with patch.object(cli, "devices", return_value={}):
            self.worker()
        self.assert_closed()
        self.control.assert_not_called()

    def test_armed_worker_during_inhibition_or_monitor_loss(self):
        self.arm()
        demo.inhibit()
        self.worker()
        self.assert_closed()
        demo.INHIBIT.unlink()
        self.timer.write_text("inactive")
        with self.assertRaisesRegex(RuntimeError, "monitor unavailable"):
            self.worker()
        self.assert_closed()

    def test_enable_start_failure_and_immediate_worker(self):
        self.control.side_effect = OSError("start refused")
        with self.assertRaisesRegex(RuntimeError, "start refused.*policy disabled.*confirmed inactive"):
            self.arm()
        self.assertFalse(demo.read_policy()["enabled"])
        self.control.reset_mock()
        self.worker()
        self.control.assert_not_called()
        self.assert_closed()

    def test_unconfirmed_start_rolls_back(self):
        self.control.side_effect = None  # Accept the request without starting the service.
        with self.assertRaisesRegex(RuntimeError, "start not confirmed.*policy disabled"):
            self.arm()
        self.assertFalse(demo.read_policy()["enabled"])
        self.assert_closed()

    def test_grant_creation_failure(self):
        with patch.object(demo, "open_grant", side_effect=PermissionError("grant denied")):
            with self.assertRaisesRegex(RuntimeError, "grant denied.*policy disabled"):
                self.arm()
        self.assert_closed()
        self.control.assert_not_called()

    def test_failed_policy_commit_and_rollback_write(self):
        # Exercise an ambiguous write outcome: the policy reached disk before the error.
        save = demo.save_policy
        def unreliable(policy):
            if policy["enabled"]:
                save(policy)
                raise OSError("enable commit failed")
            raise OSError("rollback write failed")
        with patch.object(demo, "save_policy", side_effect=unreliable):
            with self.assertRaisesRegex(RuntimeError, "enable commit failed.*rollback write failed.*inhibited"):
                self.arm()
        self.assertTrue(demo.read_policy()["enabled"])
        self.assertTrue(demo.inhibited())
        self.worker()
        self.assert_closed()
        with self.assertRaisesRegex(RuntimeError, "disable the demo"):
            self.monitor(True)
        self.disable()
        self.monitor(True)
        self.assertFalse(demo.inhibited())
        self.assertFalse(demo.read_policy()["enabled"])

    def test_commit_failure_and_grant_revocation_failure(self):
        save = demo.save_policy
        def write(policy):
            if policy["enabled"]:
                raise OSError("commit failed")
            save(policy)
        with patch.object(demo, "save_policy", side_effect=write), \
             patch.object(demo, "revoke", side_effect=OSError("unlink failed")):
            with self.assertRaisesRegex(RuntimeError, "commit failed.*policy disabled.*unlink failed.*confirmed inactive"):
                self.arm()
        self.assertTrue(demo.GRANT.exists())
        self.worker()
        self.assert_closed()

    def test_unreachable_manager_during_rollback(self):
        def start(*args):
            self.show.side_effect = RuntimeError("bus unavailable")
            raise subprocess.TimeoutExpired("start", 15)
        self.control.side_effect = start
        with self.assertRaisesRegex(RuntimeError, "timed out.*policy disabled.*bus unavailable.*inactivity unconfirmed"):
            self.arm()
        self.assertFalse(demo.read_policy()["enabled"])
        self.assertFalse(demo.GRANT.exists())

    def test_disable_preserves_stop_timeout_even_if_inactive(self):
        self.arm()
        def stop(*args):
            self.actuate(*args)
            raise subprocess.TimeoutExpired("stop", 15)
        self.control.side_effect = stop
        with self.assertRaisesRegex(RuntimeError, "policy disabled.*timed out.*confirmed inactive"):
            self.disable()
        self.assertFalse(demo.read_policy()["enabled"])
        self.worker()
        self.assert_closed()

    def test_failed_stop_after_disarm_is_retried_by_worker(self):
        self.arm()
        self.control.side_effect = OSError("stop failed")
        with self.assertRaisesRegex(RuntimeError, "policy disabled.*stop failed.*inactivity unconfirmed"):
            self.disable()
        self.assertFalse(demo.read_policy()["enabled"])
        self.assertEqual(self.service.read_text(), "active")
        self.control.side_effect = self.actuate
        self.worker()
        self.assert_closed()

    def test_disable_write_failure_inhibits_next_worker(self):
        self.arm()
        with patch.object(demo, "save_policy", side_effect=OSError("read-only policy")):
            with self.assertRaisesRegex(RuntimeError, "still armed.*read-only policy.*inhibited"):
                self.disable()
        self.assertTrue(demo.read_policy()["enabled"])
        self.worker()
        self.assert_closed()

    def test_disable_reports_loss_of_both_persistent_controls(self):
        self.arm()
        with patch.object(demo, "inhibit", side_effect=OSError("marker unavailable")), \
             patch.object(demo, "save_policy", side_effect=OSError("write denied")):
            with self.assertRaisesRegex(RuntimeError, "still armed.*marker unavailable.*startup may still be possible"):
                self.disable()
        self.assert_closed()
        self.assertTrue(demo.read_policy()["enabled"])
        self.assertFalse(demo.inhibited())

    def test_disable_unsafe_unit_or_grant_removal_failure(self):
        for fault in ("unit", "grant"):
            with self.subTest(fault=fault):
                self.arm()
                self.control.reset_mock()
                target = "verify_unit" if fault == "unit" else "revoke"
                with patch.object(demo, target, side_effect=RuntimeError("injected fault")):
                    with self.assertRaisesRegex(RuntimeError, "policy disabled.*injected fault"):
                        self.disable()
                self.assertFalse(demo.read_policy()["enabled"])
                if fault == "unit":
                    self.control.assert_not_called()
                else:
                    self.control.assert_called_once_with("stop", demo.SERVICE)
                self.worker()
                self.assert_closed()
                self.monitor(True)

    def test_corrupt_policy_on_disable_inhibits_and_closes(self):
        self.arm()
        demo.POLICY.write_text("bad JSON")
        with self.assertRaisesRegex(RuntimeError, "unreadable policy.*inhibited.*confirmed inactive"):
            self.disable()
        self.assertTrue(demo.inhibited())
        self.assert_closed()

    def test_monitor_enable_failure_leaves_opening_inhibited(self):
        self.monitor(False)
        def fail(args, **kwargs):
            if args[1] == "start":
                raise OSError("worker start failed")
            self.configure(args, **kwargs)
        with patch.object(subprocess, "run", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "worker start failed.*inhibited"):
                self.monitor(True)
        self.assertTrue(cli.RULE.is_file())
        self.assertEqual(self.state(cli.TIMER), "active")
        with self.assertRaisesRegex(RuntimeError, "inhibited"):
            self.arm()
        self.monitor(True)
        self.arm()
        self.assertTrue(demo.read_policy()["enabled"])

    def test_repeat_monitor_recovery_after_timer_error(self):
        def fail(args, **kwargs):
            if args[1] == "disable":
                raise OSError("timer refused")
            self.configure(args, **kwargs)
        with patch.object(subprocess, "run", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "timer refused.*authorization inhibited"):
                self.monitor(False)
        with self.assertRaisesRegex(RuntimeError, "inhibited"):
            self.arm()
        for enabled in (False, False, True, True):
            self.monitor(enabled)
            self.assertEqual(cli.RULE.exists(), enabled)
            self.assertEqual(self.timer.read_text(), "active" if enabled else "inactive")
            self.assertFalse(demo.inhibited())

    def test_monitor_requires_worker_and_timer_confirmation(self):
        for unit in (cli.SERVICE, cli.TIMER):
            with self.subTest(unit=unit), patch.object(
                cli, "unit_state", side_effect=lambda name: "transitioning" if name == unit else self.state(name)
            ):
                with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
                    self.monitor(False)
                self.assertTrue(demo.inhibited())


class ProcessTests(AdminFixture):
    """Forked CLI operations share files, never Python lock or manager state."""

    def setUp(self):
        super().setUp()
        self.ctx = multiprocessing.get_context("fork")
        self.paused = self.ctx.Event()
        self.resume = self.ctx.Event()
        self.contended = self.ctx.Event()

    def child(self, operation):
        process = self.ctx.Process(target=operation)
        process.start()
        def cleanup():
            if process.is_alive():
                process.terminate()
            process.join(5)
            process.close()
        self.addCleanup(cleanup)
        return process

    def finish(self, process, code=0):
        process.join(8)
        self.assertEqual(process.exitcode, code, "child blocked or failed")

    def pause(self):
        self.paused.set()
        self.assertTrue(self.resume.wait(8), "test barrier timed out")

    @contextmanager
    def detect_contention(self):
        flock = fcntl.flock
        def acquire(file, mode):
            try:
                flock(file, mode | fcntl.LOCK_NB)
            except BlockingIOError:
                self.contended.set()
                flock(file, mode)
        with patch.object(fcntl, "flock", side_effect=acquire):
            yield

    def test_monitor_disable_blocks_enable_but_allows_worker_to_finish(self):
        configure = cli.configure_monitor
        def monitor():
            def paused_configure(*args):
                self.pause()  # Policy checked, timer and rule still live.
                configure(*args)
            with patch.object(cli, "configure_monitor", side_effect=paused_configure):
                self.monitor(False)
        def enable():
            with self.detect_contention(), self.assertRaisesRegex(RuntimeError, "observation"):
                self.arm()
        first = self.child(monitor)
        self.assertTrue(self.paused.wait(8))
        second = self.child(enable)
        self.assertTrue(self.contended.wait(8))
        self.assertTrue(cli.RULE.exists())
        self.assertTrue(demo.inhibited())
        self.finish(self.child(self.worker))
        self.assert_closed()
        self.resume.set()
        self.finish(first)
        self.finish(second)
        self.assertFalse(demo.read_policy()["enabled"])
        self.assertFalse(cli.RULE.exists())

    def test_simultaneous_enables_only_commit_once(self):
        save = demo.save_policy
        def first_enable():
            def paused_commit(policy):
                if policy["enabled"]:
                    self.pause()
                save(policy)
            with patch.object(demo, "save_policy", side_effect=paused_commit):
                self.arm()
        def other_enable():
            with self.detect_contention(), self.assertRaisesRegex(RuntimeError, "already enabled"):
                self.arm()
        first = self.child(first_enable)
        self.assertTrue(self.paused.wait(8))
        second = self.child(other_enable)
        self.assertTrue(self.contended.wait(8))
        self.assertFalse(demo.read_policy()["enabled"])
        self.resume.set()
        self.finish(first)
        self.finish(second)
        self.assertTrue(demo.read_policy()["enabled"])
        self.assertEqual(self.service.read_text(), "active")

    def test_worker_waits_for_disable_then_observes_disarmed_policy(self):
        self.arm()
        close = demo.close_demo
        def disable():
            def paused_close():
                self.pause()
                close()
            with patch.object(demo, "close_demo", side_effect=paused_close):
                self.disable()
        def worker():
            with self.detect_contention():
                self.worker()
        first = self.child(disable)
        self.assertTrue(self.paused.wait(8))
        second = self.child(worker)
        self.assertTrue(self.contended.wait(8))
        self.assertFalse(demo.read_policy()["enabled"])
        self.resume.set()
        self.finish(first)
        self.finish(second)
        self.assert_closed()

    def test_interrupted_enable_before_and_after_commit(self):
        save = demo.save_policy
        for committed in (False, True):
            def interrupted():
                def commit(policy):
                    if committed:
                        save(policy)
                    os._exit(23)  # Release locks without executing exception handlers.
                with patch.object(demo, "save_policy", side_effect=commit):
                    self.arm()
            with self.subTest(committed=committed):
                self.finish(self.child(interrupted), 23)
                self.assertTrue(demo.GRANT.exists())
                self.assertEqual(demo.read_policy()["enabled"], committed)
                self.worker()
                if committed:
                    self.assertEqual(self.service.read_text(), "active")
                    self.disable()
                self.assert_closed()

    def test_crashed_monitor_and_worker_do_not_clear_veto(self):
        def interrupt_monitor():
            with patch.object(cli, "configure_monitor", side_effect=lambda *_: os._exit(22)):
                self.monitor(False)
        def interrupt_worker():
            with patch.object(demo, "close_demo", side_effect=lambda: os._exit(23)):
                self.worker()
        self.finish(self.child(interrupt_monitor), 22)
        self.finish(self.child(interrupt_worker), 23)
        self.assertTrue(demo.inhibited())
        with self.assertRaisesRegex(RuntimeError, "inhibited"):
            self.arm()
        self.monitor(False)
        self.assertFalse(demo.inhibited())
        self.assertFalse(cli.RULE.exists())

    def test_interrupted_disable_veto_survives_loss_of_runtime_state(self):
        self.arm()
        def interrupt_disable():
            with patch.object(demo, "save_policy", side_effect=lambda *_: os._exit(24)):
                self.disable()
        self.finish(self.child(interrupt_disable), 24)
        self.assertTrue(demo.read_policy()["enabled"])
        for path in cli.RUNTIME.iterdir():
            path.unlink()
        self.service.write_text("inactive")
        self.worker()
        self.assertTrue(demo.inhibited())
        self.assert_closed()
        self.disable()
        self.monitor(False)
        self.assertFalse(demo.inhibited())

    def test_monitor_waits_for_worker_already_scanning(self):
        def worker():
            def scan():
                self.pause()
                return self.present
            cli.observe_once(scan=scan, current_boot="test")
        def monitor():
            with self.detect_contention():
                self.monitor(False)
        first = self.child(worker)
        self.assertTrue(self.paused.wait(8))
        second = self.child(monitor)
        self.assertTrue(self.contended.wait(8))
        self.assertFalse(demo.inhibited())
        self.resume.set()
        self.finish(first)
        self.finish(second)
        self.assertFalse(cli.RULE.exists())
