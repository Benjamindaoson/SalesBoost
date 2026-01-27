from typing import Dict, Any


class Router:
    def __init__(self):
        self.history = []

    def route_message(self, message: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Simple deterministic routing: choose model based on presence of 'force_model' flag
        self.history.append({"message": message, "context": context})
        if message.get("force_model") == "legacy":
            chosen = "legacy_model"
        else:
            chosen = "default_model"
        return {"next_model": chosen, "routed_at": True}
