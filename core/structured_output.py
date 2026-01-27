import ast
import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Type

from pydantic import BaseModel, ValidationError

_CODE_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.MULTILINE)
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


@dataclass
class ParseResult:
    data: Optional[Any]
    success: bool
    error: Optional[str]
    cleaned_text: str
    attempts: List[str]


def _strip_code_fences(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text or "").strip()


def _extract_json_blob(text: str) -> str:
    if not text:
        return ""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _clean_json(text: str) -> str:
    cleaned = _strip_code_fences(text)
    cleaned = _extract_json_blob(cleaned)
    cleaned = _TRAILING_COMMA_RE.sub(r"\1", cleaned)
    return cleaned.strip()


def _try_json_load(text: str) -> Any:
    return json.loads(text)


def _try_literal_eval(text: str) -> Any:
    return ast.literal_eval(text)


def parse_json_with_fallback(raw_text: str) -> ParseResult:
    attempts: List[str] = []
    cleaned = _clean_json(raw_text or "")
    if not cleaned:
        return ParseResult(None, False, "empty_output", cleaned, attempts)

    for attempt_name, parser in [("json", _try_json_load), ("literal_eval", _try_literal_eval)]:
        try:
            attempts.append(attempt_name)
            return ParseResult(parser(cleaned), True, None, cleaned, attempts)
        except Exception as exc:
            attempts.append(f"{attempt_name}_failed:{exc.__class__.__name__}")

    return ParseResult(None, False, "parse_failed", cleaned, attempts)


def parse_model_output(
    raw_text: str,
    schema: Type[BaseModel],
) -> ParseResult:
    json_result = parse_json_with_fallback(raw_text)
    if not json_result.success or json_result.data is None:
        return json_result

    try:
        model = schema.model_validate(json_result.data)
        return ParseResult(model, True, None, json_result.cleaned_text, json_result.attempts)
    except ValidationError as exc:
        return ParseResult(None, False, f"schema_validation_failed:{exc.__class__.__name__}", json_result.cleaned_text, json_result.attempts)
