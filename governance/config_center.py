from typing import Dict


class GovernanceConfigCenter:
    def __init__(self):
        self.policies: Dict[str, Dict[str, object]] = {}

    def set_policy(self, name: str, payload: Dict[str, object]):
        self.policies[name] = payload

    def get_policy(self, name: str) -> Dict[str, object]:
        return self.policies.get(name, {})
