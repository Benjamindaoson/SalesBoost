from .events import RoundEvent

class Round:
    def __init__(self, round_id: str):
        self.round_id = round_id
        self.active = False

    def start(self):
        self.active = True
        return {"event": RoundEvent.START, "round_id": self.round_id}

    def end(self, payload=None):
        self.active = False
        return {"event": RoundEvent.END, "round_id": self.round_id, "payload": payload}

    def abort(self, reason: str):
        self.active = False
        return {
            "event": RoundEvent.ABORT,
            "round_id": self.round_id,
            "reason": reason,
        }
