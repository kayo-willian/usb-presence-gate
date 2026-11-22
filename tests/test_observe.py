import unittest
from usbgate.observe import advance


class ObserveTests(unittest.TestCase):
    def test_silent_removal_completes(self):
        state, _, _ = advance({}, {"a"}, 10, "boot")
        state, events, wait = advance(state, set(), 12, "boot", 10)
        self.assertEqual(events, [("device_absence_pending", "a")])
        self.assertEqual(wait, 10)
        state, events, wait = advance(state, set(), 22, "boot", 10)
        self.assertEqual(events, [("device_absent", "a")])
        self.assertIsNone(wait)

    def test_restart_does_not_extend_grace(self):
        state, _, _ = advance({}, {"a"}, 1, "boot")
        state, _, _ = advance(state, set(), 5, "boot", 10)
        state, events, wait = advance(state, set(), 11, "boot", 10)
        self.assertEqual(state["devices"]["a"]["absent_since"], 5)
        self.assertEqual(events, [])
        self.assertEqual(wait, 4)

    def test_reappearance_resets_absence(self):
        state, _, _ = advance({}, {"a"}, 1, "boot")
        state, _, _ = advance(state, set(), 5, "boot")
        state, events, wait = advance(state, {"a"}, 6, "boot")
        self.assertIsNone(state["devices"]["a"]["absent_since"])
        self.assertEqual(events, [("device_returned", "a")])
        self.assertIsNone(wait)

    def test_previous_boot_discarded(self):
        old = {"boot_id": "old", "devices": {"a": {"state": "present", "absent_since": None}}}
        state, _, _ = advance(old, set(), 1, "new")
        self.assertEqual(state["devices"], {})

    def test_idempotence(self):
        state, _, _ = advance({}, {"a"}, 1, "boot")
        same, events, wait = advance(state, {"a"}, 2, "boot")
        self.assertEqual(same, state)
        self.assertEqual(events, [])
        self.assertIsNone(wait)

    def test_invalid_grace(self):
        with self.assertRaises(ValueError):
            advance({}, set(), 2, "boot", -1)
