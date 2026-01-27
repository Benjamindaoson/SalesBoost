import unittest
from phaseB.router_unification import Router


class PhaseBTest(unittest.TestCase):
    def test_router_unification(self):
        r = Router()
        out = r.route_message({"text": "hello"}, {})
        self.assertIn("next_model", out)


if __name__ == "__main__":
    unittest.main()
