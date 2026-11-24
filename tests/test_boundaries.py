"""Fixed-unit safety checks with staged packaging files and a simulated system manager."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import call, patch

from usbgate import cli, demo, policy


def properties(name):
    # Debian system manager defaults relevant to the three shipped units.
    data = dict.fromkeys((*policy.FIELDS, *policy.EXTRA_RELATIONS), "")
    data.update(dict.fromkeys(policy.ACTIONS, "none"))
    data.update(Id=name, Names=name, LoadState="loaded", FragmentPath=f"/etc/systemd/system/{name}",
                Transient="no", NeedDaemonReload="no", CanStart="yes", CanStop="yes",
                Type="simple", Slice="system.slice", DynamicUser="yes", RefuseManualStop="no", RefuseManualStart="no",
                Job="", ActiveState="inactive", SubState="dead", Conflicts="shutdown.target",
                Requires="sysinit.target system.slice", Wants="tmp.mount")
    if name == cli.TIMER:
        data.update(Requires="sysinit.target", Wants="", WantedBy="timers.target", Triggers=cli.SERVICE,
                    Unit=cli.SERVICE, UnitFileState="enabled", ActiveState="active", SubState="waiting")
    elif name == cli.SERVICE:
        data["TriggeredBy"] = cli.TIMER
    return data


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        units = self.root / "units"
        units.mkdir()
        self.link = units / "timers.target.wants" / cli.TIMER
        self.link.parent.mkdir()
        self.link.symlink_to(Path("..") / cli.TIMER)
        for module, name, value in (
            (demo, "TRUST_ROOT", self.root), (demo, "TRUST_UID", os.getuid()),
            (demo, "MANIFEST", self.root / "manifest"), (demo, "SYSTEM_UNITS", units),
            (demo, "UNIT", units / demo.SERVICE), (demo, "RULE", self.root / "rule"),
            (cli, "RULE", self.root / "rule"), (cli, "SOURCE_RULE", self.root / "reference"),
            (demo, "GRANT", self.root / "grant"), (demo, "POLICY", self.root / "etc/policy"),
            (demo, "INHIBIT", self.root / "inhibit"), (cli, "RUNTIME", self.root),
            (cli, "LOCK", self.root / "lock"), (cli, "STATE", self.root / "cache"),
        ):
            self.enterContext(patch.object(module, name, value))
        packaging = Path(__file__).resolve().parents[1] / "packaging"
        digests = {}
        for src, dest in [(p, units / p.name) for p in (packaging / "systemd").iterdir()] + [
            (packaging / "udev/70-usbgate.rules", cli.SOURCE_RULE)
        ]:
            content = src.read_bytes()
            dest.write_bytes(content)
            digests[str(dest)] = hashlib.sha256(content).hexdigest()
        demo.MANIFEST.write_text(json.dumps({"schema_version": 1, "files": digests}))
        demo.RULE.write_bytes(cli.SOURCE_RULE.read_bytes())
        self.units = {name: properties(name) for name in (demo.SERVICE, cli.TIMER, cli.SERVICE)}
        self.key = "a" * 12
        self.observed = {self.key: {"assurance": "identifier-only", "classes": ["08"]}}
        self.state = {"devices": {self.key: {"state": "present"}}}
        self.policy = {"schema_version": 1, "enabled": True, "fingerprint": self.key}
        demo.save_policy(self.policy)
        self.run = self.enterContext(patch.object(subprocess, "run", side_effect=self.manager))
        self.control = self.enterContext(patch.object(demo, "systemctl", side_effect=self.actuate))
        self.enterContext(patch.object(demo, "require_root"))

    def manager(self, cmd, **kwargs):
        if cmd[1] == "show":
            props = self.units[cmd[-1]]
            fields = next(opt for opt in cmd if opt.startswith("--property=")).split("=")[1].split(",")
            text = "\n".join(f"{key}={props[key]}" for key in fields if key in props)
            return subprocess.CompletedProcess(cmd, 0, text, "")
        self.assertIn(cmd[0], ("/usr/bin/udevadm", "/usr/bin/systemctl"))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def actuate(self, verb, name):
        self.assertEqual(name, demo.SERVICE)
        self.assertIn(verb, ("start", "stop"))
        running = verb == "start"
        self.units[name].update(ActiveState="active" if running else "inactive",
                                SubState="running" if running else "dead")

    def reconcile(self):
        demo.reconcile(self.state, self.observed)

    def assert_denied(self, reason):
        with self.assertRaisesRegex(RuntimeError, reason):
            self.reconcile()
        self.assertFalse(demo.GRANT.exists())
        self.control.assert_not_called()

    def test_expected_service_and_running_timer(self):
        for sub in ("waiting", "running"):
            self.units[cli.TIMER]["SubState"] = sub
            self.reconcile()
        self.control.assert_called_once_with("start", demo.SERVICE)

    def test_demo_identity_and_stop_safety(self):
        original = self.units[demo.SERVICE]
        for field, value in (
            ("Names", demo.SERVICE + " other.service"), ("Id", "other.service"),
            ("DropInPaths", "/etc/systemd/system/service.d/override.conf"),
            ("FragmentPath", "/etc/systemd/system/other.service"), ("NeedDaemonReload", "yes"),
            ("Transient", "yes"), ("RequiredBy", "other.service"), ("BindsTo", "other.service"),
            ("RequisiteOf", "other.service"), ("Wants", "other.service"), ("Requires", "other.service"),
            ("ConflictedBy", "other.service"), ("Conflicts", "other.service"),
            ("OnSuccess", "other.service"), ("Upholds", "other.service"), ("Job", "invalid"),
            ("PropagatesStopTo", "other.service"), ("FailureAction", "reboot"),
        ):
            with self.subTest(field=field):
                self.units[demo.SERVICE] = dict(original, **{field: value})
                self.assert_denied(field)
                self.units[demo.SERVICE].update(ActiveState="active", SubState="running")
                demo.GRANT.touch()
                with self.assertRaisesRegex(RuntimeError, "unsafe to stop"):
                    demo.close_demo()
                self.assertFalse(demo.GRANT.exists())
                self.control.assert_not_called()

    def test_pending_start_is_cancelled_only_by_a_verified_stop(self):
        unit = self.units[demo.SERVICE]

        def stop(verb, name):
            self.assertFalse(demo.GRANT.exists())
            self.assertEqual(verb, "stop")
            self.actuate(verb, name)
            unit["Job"] = ""

        self.control.side_effect = stop
        for active, sub, job in (("inactive", "dead", "45"), ("active", "running", "45"),
                                 ("activating", "start", "45"), ("activating", "start", ""),
                                 ("deactivating", "stop-sigterm", "45")):
            with self.subTest(active=active, job=job):
                demo.GRANT.touch()
                unit.update(ActiveState=active, SubState=sub, Job=job)
                with self.assertRaisesRegex(RuntimeError, "start unsafe during transition.*confirmed inactive"):
                    self.reconcile()
                self.control.assert_called_once_with("stop", demo.SERVICE)
                self.control.reset_mock()

    def test_transition_does_not_override_structural_refusal(self):
        self.units[demo.SERVICE].update(ActiveState="activating", SubState="start", Job="45",
                                        RequiredBy="other.service")
        demo.GRANT.touch()
        self.assert_denied("RequiredBy.*unsafe to stop")
        with self.assertRaisesRegex(RuntimeError, "unsafe to stop.*RequiredBy"):
            demo.close_demo()
        self.control.assert_not_called()

    def test_pending_job_after_stop_is_not_confirmed_inactive(self):
        self.units[demo.SERVICE].update(ActiveState="activating", SubState="start", Job="45")
        # Simulate a later job still queued after stop returned and the process exited.
        with self.assertRaisesRegex(RuntimeError, "inactivity unconfirmed.*transitioning"):
            demo.close_demo()
        self.control.assert_called_once_with("stop", demo.SERVICE)

    def test_missing_and_duplicate_properties(self):
        del self.units[demo.SERVICE]["OnSuccess"]
        self.assert_denied("incomplete")
        self.run.side_effect = lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, "Id=a\nId=b", "")
        self.assert_denied("malformed")

    def test_timer_authorization_matrix(self):
        original = self.units[cli.TIMER]
        for field, value in (
            ("UnitFileState", "disabled"), ("UnitFileState", "enabled-runtime"),
            ("UnitFileState", "unexpected"), ("LoadState", "masked"), ("LoadState", "not-found"),
            ("ActiveState", "failed"), ("ActiveState", "inactive"), ("ActiveState", "activating"),
            ("SubState", "elapsed"), ("Job", "27"), ("Id", "other.timer"),
            ("Unit", "other.service"), ("Triggers", "other.service"),
            ("NeedDaemonReload", "yes"), ("DropInPaths", "override.conf"),
        ):
            with self.subTest(field=field, value=value):
                self.units[cli.TIMER] = dict(original, **{field: value})
                self.assert_denied(field)

    def test_live_grant_revoked_if_timer_becomes_runtime_only(self):
        self.reconcile()
        self.units[cli.TIMER]["UnitFileState"] = "enabled-runtime"
        with self.assertRaisesRegex(RuntimeError, "enabled-runtime.*confirmed inactive"):
            self.reconcile()
        self.assertEqual(self.control.call_args_list, [call("start", demo.SERVICE), call("stop", demo.SERVICE)])
        self.assertFalse(demo.GRANT.exists())

    def test_timer_and_worker_files_and_target_link(self):
        for path in (demo.SYSTEM_UNITS / cli.TIMER, demo.SYSTEM_UNITS / cli.SERVICE):
            content = path.read_bytes()
            path.write_bytes(content + b"# drift")
            self.assert_denied("differs from manifest")
            path.write_bytes(content)
        self.link.unlink()
        self.assert_denied("enablement link")
        self.link.symlink_to(demo.UNIT)
        self.assert_denied("enablement link")

    def test_timer_query_failure_does_not_hide_unsafe_stop(self):
        def unavailable(cmd, **kw):
            if cmd[-1] == cli.TIMER:
                raise subprocess.TimeoutExpired(cmd, 10)
            if cmd[-1] == demo.SERVICE and self.units[demo.SERVICE]["ActiveState"] == "active":
                self.units[demo.SERVICE]["RequiredBy"] = "other.service"
            return self.manager(cmd, **kw)
        self.reconcile()
        self.control.reset_mock()
        # The stop preflight sees a relationship added after the timer query failed.
        def drift(cmd, **kw):
            if cmd[-1] == cli.TIMER:
                self.run.side_effect = unavailable
                raise subprocess.TimeoutExpired(cmd, 10)
            return self.manager(cmd, **kw)
        self.run.side_effect = drift
        self.assert_denied("timed out.*unsafe to stop.*RequiredBy")

    def test_udev_missing_changed_and_symlink(self):
        demo.RULE.write_text("different")
        self.assert_denied("rule differs")
        demo.RULE.unlink()
        self.assert_denied("No such file")
        demo.RULE.symlink_to(cli.SOURCE_RULE)
        self.assert_denied("symbolic links")

    def test_matching_modified_reference_and_deployment(self):
        demo.RULE.write_text("changed together")
        cli.SOURCE_RULE.write_bytes(demo.RULE.read_bytes())
        self.assert_denied("differs from manifest")

    def test_rule_changes_while_initial_enable_commits_sample(self):
        demo.save_policy(dict(self.policy, enabled=False))
        save = cli.save_state
        def save_with_drift(data):
            save(data)
            demo.RULE.write_text("changed while recording observation")
        with patch.object(cli, "devices", return_value=self.observed), patch.object(cli, "save_state", save_with_drift):
            with self.assertRaisesRegex(RuntimeError, "rule differs.*policy disabled"):
                demo.enable()
        self.assertFalse(demo.GRANT.exists())
        self.control.assert_not_called()

    def test_udev_drift_rechecked_after_arming(self):
        self.reconcile()
        demo.RULE.write_text("changed rule")
        with self.assertRaisesRegex(RuntimeError, "rule differs.*confirmed inactive"):
            self.reconcile()
        self.assertFalse(demo.GRANT.exists())
        self.assertEqual(self.control.call_args_list[-1], call("stop", demo.SERVICE))

    def test_untrusted_permissions_and_ownership(self):
        for path in (demo.RULE, cli.SOURCE_RULE, demo.MANIFEST, demo.UNIT, demo.SYSTEM_UNITS):
            with self.subTest(path=path):
                mode = path.stat().st_mode
                path.chmod(mode | 0o020)
                self.assert_denied("untrusted")
                path.chmod(mode)
        with patch.object(demo, "TRUST_UID", os.getuid()+1):
            self.assert_denied("untrusted")

    def test_reference_manifest_and_directory_symlinks(self):
        for path in (cli.SOURCE_RULE, demo.MANIFEST, demo.SYSTEM_UNITS):
            with self.subTest(path=path):
                moved = path.with_name(path.name + "-saved")
                path.rename(moved)
                path.symlink_to(moved)
                self.assert_denied("symbolic links|untrusted directory")
                path.unlink()
                moved.rename(path)

    def test_nonregular_rule_and_read_failure(self):
        demo.RULE.unlink()
        os.mkfifo(demo.RULE)
        self.assert_denied("untrusted file type")
        demo.RULE.unlink()
        demo.RULE.write_bytes(cli.SOURCE_RULE.read_bytes())
        real_read = demo.trusted_bytes
        def denied(path):
            if path == demo.RULE:
                raise PermissionError("rule read denied")
            return real_read(path)
        with patch.object(demo, "trusted_bytes", side_effect=denied):
            self.assert_denied("rule read denied")

    def test_diagnostics_distinguish_activity_and_readiness(self):
        self.assertEqual(cli.monitor_diagnostic(), "verified")
        self.units[cli.TIMER]["UnitFileState"] = "disabled"
        self.assertTrue(cli.timer_active())
        self.assertIn("UnitFileState", cli.monitor_diagnostic())

    def test_unusable_manifest(self):
        content = demo.MANIFEST.read_bytes()
        for broken in (b"{}", b"garbled", b'{"schema_version":1,"files":{}}'):
            demo.MANIFEST.write_bytes(broken)
            self.assert_denied("invalid install manifest")
        demo.MANIFEST.unlink()
        self.assert_denied("invalid install manifest")
        demo.MANIFEST.write_bytes(content)
        cli.SOURCE_RULE.unlink()
        self.assert_denied("No such file")

    def test_monitor_enable_checks_after_setup_and_preserves_inhibit(self):
        demo.save_policy(dict(self.policy, enabled=False))
        self.units[cli.TIMER].update(UnitFileState="disabled", ActiveState="inactive", SubState="dead")
        with self.assertRaisesRegex(RuntimeError, "unconfirmed"):
            cli.monitor(True)
        self.assertTrue(demo.inhibited())
        self.units[cli.TIMER].update(ActiveState="active", SubState="waiting", UnitFileState="enabled-runtime")
        with self.assertRaisesRegex(RuntimeError, "enabled-runtime"):
            cli.monitor(True)
        self.assertTrue(demo.inhibited())
        self.units[cli.TIMER]["UnitFileState"] = "enabled"
        cli.monitor(True)
        self.assertFalse(demo.inhibited())

    def simulate_monitor_shutdown(self, *, timer_changes=None, leave_link=False, worker_changes=None):
        demo.save_policy(dict(self.policy, enabled=False))

        def manager(cmd, **kwargs):
            if tuple(cmd[1:]) == ("disable", "--now", cli.TIMER):
                timer = self.units[cli.TIMER]
                timer.update(ActiveState="inactive", SubState="dead", Job="", UnitFileState="disabled", WantedBy="")
                timer.update(timer_changes or {})
                if not leave_link:
                    self.link.unlink(missing_ok=True)
            elif tuple(cmd[1:]) == ("stop", cli.SERVICE):
                self.units[cli.SERVICE].update(worker_changes or {})
            return self.manager(cmd, **kwargs)

        self.run.side_effect = manager

    def test_shutdown_releases_inhibit_only_after_disabled_and_inactive(self):
        self.simulate_monitor_shutdown()
        cli.monitor(False)
        self.assertFalse(self.link.exists())
        self.assertFalse(demo.inhibited())
        self.link.parent.rmdir()  # An already disabled installation may have no wants directory.
        cli.monitor(False)
        self.assertFalse(demo.inhibited())

    def test_shutdown_inhibits_on_incomplete_manager_disablement(self):
        for field, value in (("UnitFileState", "enabled"), ("UnitFileState", "enabled-runtime"),
                             ("UnitFileState", "masked"), ("UnitFileState", ""),
                             ("WantedBy", "timers.target"), ("Job", "123"),
                             ("SubState", "waiting"), ("ActiveState", "active")):
            with self.subTest(field=field, value=value):
                self.units[cli.TIMER] = properties(cli.TIMER)
                self.simulate_monitor_shutdown(timer_changes={field: value})
                with self.assertRaisesRegex(RuntimeError, "authorization inhibited"):
                    cli.monitor(False)
                self.assertTrue(demo.inhibited())

    def test_shutdown_rejects_existing_and_dangling_boot_links(self):
        for target in (self.link.parent.parent / cli.TIMER, self.root / "missing"):
            self.link.unlink(missing_ok=True)
            self.link.symlink_to(target)
            self.simulate_monitor_shutdown(leave_link=True)
            with self.assertRaisesRegex(RuntimeError, "enablement link still present"):
                cli.monitor(False)
            self.assertTrue(demo.inhibited())
            self.assertTrue(self.link.is_symlink())

    def test_disabled_timer_with_pending_observer_does_not_clear_marker(self):
        self.simulate_monitor_shutdown(worker_changes={"Job": "72"})
        with self.assertRaisesRegex(RuntimeError, "observer shutdown unconfirmed"):
            cli.monitor(False)
        self.assertTrue(demo.inhibited())

    def test_shutdown_retains_inhibit_when_boot_link_lookup_fails(self):
        self.simulate_monitor_shutdown()
        lstat = Path.lstat

        def lookup(path):
            if path == self.link:
                raise PermissionError("cannot inspect boot link")
            return lstat(path)

        with patch.object(Path, "lstat", lookup), self.assertRaisesRegex(RuntimeError, "cannot inspect boot link"):
            cli.monitor(False)
        self.assertTrue(demo.inhibited())

    def test_armed_monitor_shortcut_closes_on_rule_drift(self):
        self.reconcile()
        demo.RULE.write_text("operator change")
        with self.assertRaisesRegex(RuntimeError, "rule differs.*confirmed inactive"):
            cli.monitor(True)
        self.assertTrue(demo.inhibited())
        self.assertFalse(demo.GRANT.exists())
        self.assertEqual(demo.RULE.read_text(), "operator change")

    def test_worker_substitution_blocks_monitor_start(self):
        demo.save_policy(dict(self.policy, enabled=False))
        self.units[cli.SERVICE]["FragmentPath"] = "/run/systemd/system/other.service"
        with self.assertRaisesRegex(RuntimeError, "FragmentPath"):
            cli.monitor(True)
        self.assertTrue(demo.inhibited())
        verbs = [c.args[0][1] for c in self.run.call_args_list]
        self.assertNotIn("enable", verbs)
        self.assertNotIn("start", verbs)
