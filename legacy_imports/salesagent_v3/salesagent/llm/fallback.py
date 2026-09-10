"""Fallback chain: primary → secondary → local."""
from __future__ import annotations

from salesagent.core.settings import settings

FALLBACK_CHAIN: list[str] = [
    settings.primary_response_model,   # Claude Sonnet
    settings.guard_model,              # GPT-4o-mini
    "gpt-4o-mini",                     # explicit fallback
]
