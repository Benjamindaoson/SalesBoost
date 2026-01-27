import unittest
from phaseA.audit_gate import AuditGate
from phaseA.round_events import create_round_event, RoundEventType


class PhaseATest(unittest.TestCase):
    def test_audit_gate_basic(self):
        gate = AuditGate()
        ok, rec = gate.audit("hello world", {"restricted_keywords": ["secret"]})
        self.assertTrue(ok)
        bad, rec2 = gate.audit("this contains secret", {"restricted_keywords": ["secret"]})
        self.assertFalse(bad)

    def test_round_event(self):
        ev = create_round_event(RoundEventType.ROUND_START, "r1", {"info": "start"})
        self.assertEqual(ev.event_type, RoundEventType.ROUND_START)
        self.assertEqual(ev.round_id, "r1")
        self.assertIn("timestamp", ev.__dict__)


if __name__ == "__main__":
    unittest.main()
