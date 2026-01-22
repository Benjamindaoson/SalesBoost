class _MockResponse:
    def __init__(self, content: str, additional_kwargs: dict | None = None):
        self.content = content
        self.additional_kwargs = additional_kwargs or {}


class ChatOpenAI:
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get("model", "mock-model")

    async def ainvoke(self, messages, **kwargs):
        return _MockResponse(
            content="【MOCK】这是一个占位回复，用于打通 e2e 流程。",
            additional_kwargs={},
        )

    def invoke(self, messages, **kwargs):
        return _MockResponse(
            content="【MOCK】这是一个占位回复，用于打通 e2e 流程。",
            additional_kwargs={},
        )
