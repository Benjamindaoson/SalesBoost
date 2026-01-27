"""PromptService stub."""


class PromptService:
    def __init__(self, settings=None):
        self.settings = settings

    def render(self, name: str, **kwargs) -> str:
        return f"Prompt:{name}"
