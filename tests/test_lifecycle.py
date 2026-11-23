import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from usbgate import cli, demo, install


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
                 patch.object(demo, "reconcile"), \
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
            with patch.object(cli, "RUNTIME", root), \
                 patch.object(cli, "LOCK", root / "lock"), \
                 patch.object(demo, "INHIBIT", root / "inhibit"), \
                 patch.object(demo, "close_demo"), \
                 patch.object(cli, "RULE", rule), \
                 patch.object(cli, "SOURCE_RULE", source), \
                 patch.object(demo, "POLICY", root / "demo.json"), \
                 patch.object(cli, "has_enrollment", return_value=False), \
                 patch.object(cli.os, "geteuid", return_value=0), \
                 patch.object(cli.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(RuntimeError):
                    cli.monitor(False)
            self.assertFalse(rule.exists())
            self.assertEqual(called, ["disable", "control", "stop"])


class DeviceScanTests(unittest.TestCase):
    @staticmethod
    def add_usb(root, bus, serial=None, device_class="08"):
        device = root / bus
        device.mkdir()
        (device / "idVendor").write_text("abcd")
        (device / "idProduct").write_text("1234")
        if serial is not None:
            (device / "serial").write_text(serial)
        interface = root / f"{bus}:1.0"
        interface.mkdir()
        (interface / "bInterfaceClass").write_text(device_class)

    def test_duplicate_usb_identity_is_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.add_usb(root, "1-3", serial="fictional-serial")
            self.add_usb(root, "1-5", serial="fictional-serial", device_class="03")
            matches = cli.devices(root)
            self.assertEqual(len(matches), 1)
            item = next(iter(matches.values()))
            self.assertEqual(item["assurance"], "ambiguous")
            self.assertEqual(item["instances"], 2)
            self.assertEqual(item["buses"], ["1-3", "1-5"])
            self.assertEqual(item["classes"], ["03", "08"])
            self.assertNotIn("bus", item)
            self.assertNotIn("fictional-serial", str(matches))

    def test_unique_and_serialless_descriptors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.add_usb(root, "1-3", serial="fictional-serial")
            self.add_usb(root, "1-5", serial=None)
            matches = list(cli.devices(root).values())
            self.assertEqual(sorted(item["assurance"] for item in matches),
                             ["identifier-only", "weak"])
            self.assertTrue(all("bus" in item for item in matches))

    def test_three_clones_remain_ambiguous(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for bus in ("1-3", "1-5", "1-7"):
                self.add_usb(root, bus, serial="fictional-serial")
            item = next(iter(cli.devices(root).values()))
            self.assertEqual(item["instances"], 3)
            self.assertEqual(item["buses"], ["1-3", "1-5", "1-7"])


class AdditionalLifecycleTests(unittest.TestCase):
    def test_symlink_parent_blocks_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            external = Path(directory) / "external"
            root.mkdir()
            external.mkdir()
            (root / "usr").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, "symlink parent refused"):
                install.install(root)
            self.assertFalse((root / "var/lib/usbgate/install-manifest.json").exists())
            self.assertEqual(list(external.iterdir()), [])

    def test_foreign_rule_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, rule = root / "source", root / "rule"
            source.write_text("owned")
            rule.write_text("foreign")
            with patch.object(cli, "RUNTIME", root), \
                 patch.object(cli, "LOCK", root / "lock"), \
                 patch.object(demo, "INHIBIT", root / "inhibit"), \
                 patch.object(demo, "close_demo"), \
                 patch.object(cli, "SOURCE_RULE", source), \
                 patch.object(demo, "POLICY", root / "policy"), \
                 patch.object(cli, "RULE", rule), \
                 patch.object(cli.os, "geteuid", return_value=0), \
                 patch.object(cli.subprocess, "run") as run:
                with self.assertRaisesRegex(RuntimeError, "differs"):
                    cli.monitor(True)
                run.assert_not_called()
            self.assertEqual(rule.read_text(), "foreign")

    def test_uninstall_refuses_modified_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install.install(root)
            manifest = root / "var/lib/usbgate/install-manifest.json"
            manifest.write_text('{"schema_version": 1, "files": {}}')
            with self.assertRaisesRegex(RuntimeError, "invalid manifest"):
                install.uninstall(root)
            self.assertTrue((root / "usr/local/sbin/usbgate").is_file())

    def test_reinstall_refuses_occupied_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            install.install(root)
            with self.assertRaisesRegex(RuntimeError, "manifest present"):
                install.install(root)
            self.assertTrue((root / "usr/local/sbin/usbgate").is_file())

    def test_interrupted_copy_leaves_no_installed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def interrupted_copy(source, destination):
                destination.write(b"partial")
                raise OSError("simulated I/O failure")
            with patch.object(install.shutil, "copyfileobj",
                              side_effect=interrupted_copy):
                with self.assertRaisesRegex(OSError, "simulated I/O failure"):
                    install.install(root)
            self.assertFalse((root / "usr/local/sbin/usbgate").exists())
            self.assertFalse((root / "var/lib/usbgate/install-manifest.json").exists())
