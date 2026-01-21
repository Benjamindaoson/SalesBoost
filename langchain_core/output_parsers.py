import enum
from typing import Any, Dict, List, Optional, Tuple, Type, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic_core import PydanticUndefined


def _is_optional(annotation: Any) -> Tuple[bool, Any]:
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation)]
        if type(None) in args:
            non_none = [arg for arg in args if arg is not type(None)]
            return True, non_none[0] if non_none else None
    return False, annotation


def _mock_scalar(annotation: Any) -> Any:
    if annotation is str:
        return "mock"
    if annotation is bool:
        return False
    if annotation is int:
        return 0
    if annotation is float:
        return 0.5
    return None


def _build_mock_value(annotation: Any) -> Any:
    is_optional, inner = _is_optional(annotation)
    if is_optional:
        return None

    origin = get_origin(inner)
    if origin in {list, List}:
        return []
    if origin in {dict, Dict}:
        return {}

    if isinstance(inner, type) and issubclass(inner, enum.Enum):
        return list(inner)[0]

    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return _build_mock_model(inner)

    scalar = _mock_scalar(inner)
    if scalar is not None:
        return scalar

    return None


def _build_mock_model(model_cls: Type[BaseModel]) -> BaseModel:
    data: Dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        if field.default_factory is not None:
            data[name] = field.default_factory()
            continue
        if field.default is not PydanticUndefined:
            data[name] = field.default
            continue
        data[name] = _build_mock_value(field.annotation)
    return model_cls.model_validate(data)


class PydanticOutputParser:
    def __init__(self, pydantic_object: Type[BaseModel]):
        self.pydantic_object = pydantic_object

    def get_format_instructions(self) -> str:
        return "{}"

    def parse(self, text: str) -> BaseModel:
        return _build_mock_model(self.pydantic_object)

    async def ainvoke(self, result: Any) -> BaseModel:
        return _build_mock_model(self.pydantic_object)

    def invoke(self, result: Any) -> BaseModel:
        return _build_mock_model(self.pydantic_object)
