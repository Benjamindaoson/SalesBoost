import unittest


class PhaseDTest(unittest.TestCase):
    def test_governance_config(self):
        from governance.config_center import GovernanceConfigCenter
        gc = GovernanceConfigCenter()
        gc.set_policy("cost_limit", {"latency": 100, "budget": 0.8})
        self.assertIn("cost_limit", gc.policies)


if __name__ == "__main__":
    unittest.main()
