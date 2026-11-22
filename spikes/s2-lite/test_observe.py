"""Exercise timing and restart behavior with a simulated clock and port."""

import tempfile
import unittest
from pathlib import Path

from observe import GRACE_NS, observe


class GraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.state = Path(temp.name)
        self.now = 1_000_000_000
        self.waits = []
        self.events = []

    def advance(self, seconds):
        delta = round(seconds * 1_000_000_000)
        self.waits.append(delta)
        self.now += delta

    def worker(self, readings, wait=None):
        port = iter(readings)
        observe(self.state, lambda: next(port), lambda: self.now,
                wait or self.advance,
                lambda event, **data: self.events.append((event, data)))
        return self.events[-1]

    def test_single_removal_completes_without_another_event(self):
        event, result = self.worker([False, False])
        self.assertEqual(self.waits, [GRACE_NS])
        self.assertEqual((event, result["present"], result["rescan"]), ("complete", 0, 1))
        self.worker([False, False])
        self.assertEqual(self.waits, [GRACE_NS])

    def test_restart_waits_remaining_grace_and_rescans(self):
        def interrupt(seconds):
            self.advance(2)
            raise InterruptedError

        with self.assertRaises(InterruptedError):
            self.worker([False], interrupt)
        _, result = self.worker([False, True])
        self.assertEqual(self.waits, [2_000_000_000, GRACE_NS - 2_000_000_000])
        self.assertEqual(result["since_ns"], 1_000_000_000)
        self.assertEqual(result["present"], 1)
        self.assertFalse((self.state / "absent_since").exists())

    def test_return_observed_on_restart_clears_old_deadline(self):
        self.worker([False, False])
        self.assertEqual(self.worker([True]), ("complete", {"present": 1}))
        self.worker([False, False])
        self.assertEqual(self.waits, [GRACE_NS, GRACE_NS])
