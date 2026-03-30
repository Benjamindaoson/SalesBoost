def build_context(session: dict) -> dict:
    # MVP????????????????
    return {
        "history": session.get("history", [])[-5:],
        "persona": session.get("persona"),
        "stage": session.get("stage", "training"),
    }
