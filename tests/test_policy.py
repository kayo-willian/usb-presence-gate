import unittest
from unittest.mock import Mock
from usbgate.policy import inspect_unit, validate_name


def output(**changes):
    data = {
        "Id": "demo-gate.service",
        "Names": "demo-gate.service",
        "LoadState": "loaded",
        "FragmentPath": "/etc/systemd/system/demo-gate.service",
        "CanStop": "yes", "DropInPaths": "", "PartOf": "", "BoundBy": "",
        "PropagatesStopTo": "", "StopPropagatedFrom": "", "OnFailure": "",
        "TriggeredBy": "", "Triggers": "", "ConsistsOf": "",
        "Conflicts": "shutdown.target",
    }
    data.update(changes)
    return Mock(returncode=0, stdout="\n".join(f"{k}={v}" for k, v in data.items()))


class PolicyTests(unittest.TestCase):
    def test_reject_critical_names(self):
        for name in ("ssh.service", "sshd.socket", "systemd-logind.service",
                     "dbus.service", "NetworkManager.service",
                     "ufw.service", "nftables.service", "docker.service",
                     "usbgate-reconcile.service", "fail2ban.service"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(name)

    def test_reject_invalid_names(self):
        for name in ("../ssh.service", "demo@x.service", "a.target",
                     "a.service\n", "-x.socket", "a.service;id",
                     "a.service/thing", "", "a .service"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(name)

    def test_read_only_inspection_does_not_enroll(self):
        runner = Mock(return_value=output())
        result = inspect_unit("demo-gate.service", runner)
        self.assertEqual(result["preflight"], "passed")
        self.assertFalse(result["enrolled"])
        self.assertFalse(result["enforcement_ready"])
        args = runner.call_args.args[0]
        self.assertEqual(args[:3], ["/usr/bin/systemctl", "show", "--no-pager"])
        self.assertEqual(args[-1], "demo-gate.service")
        self.assertFalse(runner.call_args.kwargs["check"])

    def test_alias_denial(self):
        with self.assertRaises(ValueError):
            inspect_unit("demo-gate.service",
                         Mock(return_value=output(Names="demo-gate.service ssh.service")))

    def test_refuse_nonlocal_or_nonstoppable(self):
        for change in ({"LoadState": "not-found"}, {"CanStop": "no"},
                       {"FragmentPath": "/usr/lib/systemd/system/demo-gate.service"},
                       {"DropInPaths": "/etc/systemd/system/foo.service.d/extra.conf"},
                       {"Id": "other.service"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_unit("demo-gate.service", Mock(return_value=output(**change)))

    def test_refuse_stop_propagation(self):
        for change in ({"PartOf": "multi-user.target"},
                       {"BoundBy": "important.service"},
                       {"OnFailure": "critical.service"},
                       {"TriggeredBy": "demo.socket"},
                       {"Conflicts": "network.target"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_unit("demo-gate.service", Mock(return_value=output(**change)))

    def test_systemctl_error(self):
        with self.assertRaises(RuntimeError):
            inspect_unit("demo-gate.service",
                         Mock(return_value=Mock(returncode=1, stdout="")))
