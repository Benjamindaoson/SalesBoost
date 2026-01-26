import logging
from typing import Dict, Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.schemas.trace import ContextLayerInfo, ContextManifest

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenCounter:
    """Approximate token counter with optional tiktoken support."""

    def __init__(self) -> None:
        self._encoder = None
        try:
            import tiktoken

            self._encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._encoder = None

    def count(self, text: str) -> int:
        if not text:
            return 0
        if self._encoder:
            try:
                return len(self._encoder.encode(text))
            except Exception:
                pass
        return max(1, len(text) // 4)


class ContextLayer(BaseModel):
    name: str
    content: str
    priority: int
    tokens: int = 0
    truncated: bool = False
    source: str = "unknown"
    truncation_reason: Optional[str] = None


class ContextPolicy(BaseModel):
    max_total_tokens: int = 4000
    compression_threshold: float = 0.8
    layer_budgets: Dict[str, int] = Field(
        default_factory=lambda: {
            "system": 500,
            "history": 1500,
            "history_summary": 350,
            "knowledge": 1500,
            "state": 500,
        }
    )


class ContextBuilder:
    """Context assembly with budget awareness and summarization."""

    def __init__(
        self,
        policy: Optional[ContextPolicy] = None,
        summary_enabled: Optional[bool] = None,
        token_counter: Optional[TokenCounter] = None,
    ) -> None:
        self.policy = policy or ContextPolicy(max_total_tokens=settings.CONTEXT_MAX_TOKENS)
        self.summary_enabled = settings.CONTEXT_SUMMARY_ENABLED if summary_enabled is None else summary_enabled
        self._layers: Dict[str, ContextLayer] = {}
        self._token_counter = token_counter or TokenCounter()
        self._initial_total_tokens: Optional[int] = None

    def add_layer(self, name: str, content: str, priority: int = 10, source: str = "system") -> None:
        tokens = self._token_counter.count(content)
        self._layers[name] = ContextLayer(
            name=name,
            content=content,
            priority=priority,
            tokens=tokens,
            source=source,
        )

    def build(self) -> str:
        initial_total = sum(layer.tokens for layer in self._layers.values())
        self._initial_total_tokens = initial_total
        if initial_total > self.policy.max_total_tokens and self.summary_enabled:
            self._prepare_history_summary()
        current_total = sum(layer.tokens for layer in self._layers.values())
        if current_total > self.policy.max_total_tokens:
            return self._build_with_compression(current_total)
        return self._build_sorted_layers()

    def _build_sorted_layers(self) -> str:
        sorted_layers = sorted(self._layers.values(), key=lambda layer: layer.priority)
        return "\n\n".join(
            [f"### {layer.name.upper()} ###\n{layer.content}" for layer in sorted_layers if layer.content]
        )

    def _prepare_history_summary(self) -> None:
        history = self._layers.get("history")
        if not history:
            return
        history_budget = self.policy.layer_budgets.get("history", 1500)
        if history.tokens <= history_budget:
            return

        summary_budget = self.policy.layer_budgets.get("history_summary", 350)
        summary_text = self._summarize(history.content, summary_budget)
        if not summary_text:
            return
        summary_tokens = self._token_counter.count(summary_text)
        summary_priority = max(0, history.priority - 1)
        self._layers["history_summary"] = ContextLayer(
            name="history_summary",
            content=summary_text,
            priority=summary_priority,
            tokens=summary_tokens,
            source="summary",
        )

        history.content = self._tail_text(history.content, history_budget)
        history.tokens = self._token_counter.count(history.content)
        history.truncated = True
        history.truncation_reason = "summarized_older_turns"

    def _summarize(self, content: str, target_tokens: int) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return ""
        head = lines[:3]
        tail = lines[-3:] if len(lines) > 3 else []
        summary_lines = ["Summary of earlier turns:"] + head
        if tail:
            summary_lines.append("...")
            summary_lines.extend(tail)
        summary = "\n".join(summary_lines)
        keep_chars = target_tokens * 4
        return summary[:keep_chars]

    def _tail_text(self, content: str, target_tokens: int) -> str:
        keep_chars = target_tokens * 4
        if len(content) <= keep_chars:
            return content
        return content[-keep_chars:]

    def _build_with_compression(self, total_tokens: int) -> str:
        logger.warning(
            "Context budget exceeded: %s/%s. Applying compression.",
            total_tokens,
            self.policy.max_total_tokens,
        )

        sorted_layers = sorted(self._layers.values(), key=lambda layer: layer.priority)
        final_parts = []
        current_tokens = 0

        for layer in sorted_layers:
            budget = self.policy.layer_budgets.get(layer.name, 1000)
            if layer.tokens > budget:
                content = self._tail_text(layer.content, budget)
                layer.tokens = self._token_counter.count(content)
                layer.truncated = True
                layer.truncation_reason = f"Exceeded layer budget {budget}"
            else:
                content = layer.content

            if current_tokens + layer.tokens <= self.policy.max_total_tokens:
                final_parts.append(f"### {layer.name.upper()} ###\n{content}")
                current_tokens += layer.tokens
            else:
                remaining = self.policy.max_total_tokens - current_tokens
                if remaining > 10:
                    content = self._tail_text(layer.content, remaining)
                    final_parts.append(f"### {layer.name.upper()} ###\n{content}")
                    layer.tokens = remaining
                    layer.truncated = True
                    layer.truncation_reason = "Global budget limit reached"
                    current_tokens += remaining
                else:
                    layer.truncated = True
                    layer.truncation_reason = "Global budget exhausted"
                    layer.tokens = 0
                break

        return "\n\n".join(final_parts)

    def get_usage(self) -> ContextManifest:
        total_tokens = sum(layer.tokens for layer in self._layers.values())
        layer_infos = [
            ContextLayerInfo(
                name=layer.name,
                tokens=layer.tokens,
                truncated=layer.truncated,
                source=layer.source,
                truncation_reason=layer.truncation_reason,
            )
            for layer in self._layers.values()
        ]
        summary_parts = []
        for layer in layer_infos:
            status = "TRUNCATED" if layer.truncated else "FULL"
            summary_parts.append(f"{layer.name}({layer.tokens}t, {status})")

        initial_total = self._initial_total_tokens or total_tokens
        compression_ratio = total_tokens / initial_total if initial_total else 1.0
        return ContextManifest(
            layers=layer_infos,
            total_tokens=total_tokens,
            budget_limit=self.policy.max_total_tokens,
            compression_ratio=compression_ratio,
            manifest_summary=", ".join(summary_parts),
        )
