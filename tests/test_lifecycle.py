import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from usbgate import cli, install


class InstallTests(unittest.TestCase):
    def test_staging_is_inert_and_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install.install(root)
            self.assertTrue((root / "usr/local/sbin/usbgate").is_file())
            self.assertFalse((root / "etc/udev/rules.d/70-usbgate.rules").exists())
            install.uninstall(root)
            self.assertFalse((root / "usr/local/sbin/usbgate").exists())

    def test_modified_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install.install(root)
            (root / "usr/local/sbin/usbgate").write_text("changed")
            with self.assertRaisesRegex(RuntimeError, "file modified"):
                install.uninstall(root)


class ObservationTests(unittest.TestCase):
    def test_silent_removal_after_grace(self):
        found = [set(["a"]), set(), set()]
        now = [100.0]
        cache = [{}]
        events = []
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(cli, "RUNTIME", Path(directory)), \
                 patch.object(cli, "LOCK", Path(directory) / "lock"), \
                 patch.object(cli, "load_state", side_effect=lambda: cache[0]), \
                 patch.object(cli, "save_state", side_effect=lambda state: cache.__setitem__(0, state)), \
                 patch.object(cli.syslog, "syslog", side_effect=lambda *args: events.append(args)):
                cli.observe_once(scan=lambda: found.pop(0), clock=lambda: now[0],
                                 delay=lambda delta: now.__setitem__(0, now[0] + delta),
                                 current_boot="boot", grace=10)
                cli.observe_once(scan=lambda: found.pop(0), clock=lambda: now[0],
                                 delay=lambda delta: now.__setitem__(0, now[0] + delta),
                                 current_boot="boot", grace=10)
        self.assertEqual(cache[0]["devices"]["a"]["state"], "absent")
        self.assertEqual(now[0], 110.0)

    def test_disable_cleans_up_after_partial_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, rule = root / "source", root / "rule"
            source.write_text("test")
            rule.write_text("test")
            called = []
            def fake_run(args, **kwargs):
                called.append(args[1])
                if args[1] == "disable":
                    raise OSError("simulated failure")
            with patch.object(cli, "RULE", rule), \
                 patch.object(cli, "SOURCE_RULE", source), \
                 patch.object(cli, "has_enrollment", return_value=False), \
                 patch.object(cli.os, "geteuid", return_value=0), \
                 patch.object(cli.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(RuntimeError):
                    cli.monitor(False)
            self.assertFalse(rule.exists())
            self.assertEqual(called, ["disable", "stop", "control"])
