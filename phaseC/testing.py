import unittest


class PhaseCTest(unittest.TestCase):
    def test_knowledge_injection(self):
        from phaseC.knowledge_engineering import KnowledgeEngine
        ke = KnowledgeEngine()
        eid = ke.inject("test", {"foo": "bar"})
        self.assertTrue(eid.startswith("ke_"))


if __name__ == "__main__":
    unittest.main()
