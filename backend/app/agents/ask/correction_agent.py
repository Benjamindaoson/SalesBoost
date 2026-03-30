"""Correction agent stub."""


class _CorrectionService:
    async def apply(self, payload: dict) -> dict:
        return {"applied": True, "payload": payload}


correction_service = _CorrectionService()
