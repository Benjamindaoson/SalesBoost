import asyncio
from typing import Any, Iterable, List, Tuple


class _Chain:
    def __init__(self, steps: List[Any]):
        self._steps = steps

    def __or__(self, other: Any) -> "_Chain":
        return _Chain(self._steps + [other])

    async def ainvoke(self, variables: Any) -> Any:
        result = variables
        for step in self._steps:
            if hasattr(step, "ainvoke"):
                result = await step.ainvoke(result)
            elif hasattr(step, "invoke"):
                result = step.invoke(result)
            else:
                result = step(result)
        return result

    def invoke(self, variables: Any) -> Any:
        result = variables
        for step in self._steps:
            if hasattr(step, "invoke"):
                result = step.invoke(result)
            elif hasattr(step, "ainvoke"):
                result = asyncio.run(step.ainvoke(result))
            else:
                result = step(result)
        return result


class ChatPromptTemplate:
    def __init__(self, messages: Iterable[Tuple[str, str]]):
        self.messages = list(messages)

    @classmethod
    def from_messages(cls, messages: Iterable[Tuple[str, str]]) -> "ChatPromptTemplate":
        return cls(messages)

    def __or__(self, other: Any) -> _Chain:
        return _Chain([self, other])

    async def ainvoke(self, variables: Any) -> Any:
        return variables

    def invoke(self, variables: Any) -> Any:
        return variables


class PromptTemplate:
    def __init__(self, input_variables: List[str], template: str):
        self.input_variables = input_variables
        self.template = template

    def format(self, **kwargs: Any) -> str:
        return self.template.format(**kwargs)
