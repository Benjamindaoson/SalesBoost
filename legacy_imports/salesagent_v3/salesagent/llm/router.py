# Map task name → model identifier
TASK_MODEL_MAP: dict[str, str] = {
    "guard_rewrite": settings.guard_model,
    "critic": settings.primary_reasoning_model,
    "selfrag_filter": settings.guard_model,
    "compliance": settings.critic_model,
    "apo_variant": settings.primary_reasoning_model,
    "evolution_review": settings.critic_model,
    "synthetic": settings.primary_reasoning_model,
    "simulation": settings.primary_reasoning_model,
}

# Helper to get model based on task and optional lite mode override
def get_model(task: str, use_lite: bool = False) -> str:
    is_lite = settings.lite_mode or use_lite

    if task == "reasoning":
        return "deepseek-chat" if is_lite else settings.primary_reasoning_model
    if task == "response":
        return "deepseek-chat" if is_lite else settings.primary_response_model
    if task == "analyzer":
        return "deepseek-chat" if is_lite else settings.guard_model

    return TASK_MODEL_MAP.get(task, settings.primary_response_model)
