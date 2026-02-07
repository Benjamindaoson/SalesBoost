import uuid
from .round import Round
from .context import build_context
from .audit import SimpleAuditGate
from .errors import AuditBlockedError

class Orchestrator:
    """
    ?? A MVP Orchestrator?
    - ?????
    - ??????
    - ??????
    """

    def __init__(self, model_caller):
        self.model = model_caller
        self.audit = SimpleAuditGate()

    async def run_round(self, user_input: str, session: dict, emit):
        round_id = str(uuid.uuid4())
        rnd = Round(round_id)

        # RoundStart
        emit(rnd.start())

        try:
            ctx = build_context(session)
            reply = await self.model.generate(user_input, ctx)

            # ?? Gate?????????
            if not self.audit.check(reply, {"round_id": round_id}):
                raise AuditBlockedError("audit blocked output")

            # ????
            emit(rnd.end({"text": reply}))
            return reply

        except Exception as e:
            emit(rnd.abort(str(e)))
            raise
