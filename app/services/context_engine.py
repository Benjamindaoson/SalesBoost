import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.trace import ContextManifest, ContextLayerInfo

logger = logging.getLogger(__name__)

class ContextLayer(BaseModel):
    name: str
    content: str
    priority: int # 0 highest
    tokens: int = 0
    truncated: bool = False
    source: str = "unknown"
    truncation_reason: Optional[str] = None

class ContextPolicy(BaseModel):
    max_total_tokens: int = 4000
    compression_threshold: float = 0.8 # 超过 80% 开始裁剪
    layer_budgets: Dict[str, int] = {
        "system": 500,
        "history": 1500,
        "evidence": 1500,
        "state": 500,
        "memory": 600,
        "blackboard": 400,
    }

class ContextBuilder:
    """
    V3 上下文装配引擎
    负责分层加载、预算控制与隔离防污染
    """
    def __init__(self, policy: Optional[ContextPolicy] = None):
        self.policy = policy or ContextPolicy()
        self._layers: Dict[str, ContextLayer] = {}

    def add_layer(self, name: str, content: str, priority: int = 10, source: str = "system"):
        # 简单估算 token (按字符/4)
        tokens = len(content) // 4
        self._layers[name] = ContextLayer(
            name=name,
            content=content,
            priority=priority,
            tokens=tokens,
            source=source
        )

    def build(self) -> str:
        """根据预算装配最终上下文"""
        # Calculate total tokens initially
        initial_total = sum(l.tokens for l in self._layers.values())
        
        if initial_total > self.policy.max_total_tokens:
            return self._build_with_compression(initial_total)
        
        # 按优先级排序拼接
        sorted_layers = sorted(self._layers.values(), key=lambda x: x.priority)
        return "\n\n".join([f"### {l.name.upper()} ###\n{l.content}" for l in sorted_layers])

    def _build_with_compression(self, total_tokens: int) -> str:
        """执行压缩与裁剪逻辑"""
        logger.warning(f"Context budget exceeded: {total_tokens}/{self.policy.max_total_tokens}. Compressing...")
        
        # 简单策略：按优先级保留，低优先级裁剪
        sorted_layers = sorted(self._layers.values(), key=lambda x: x.priority)
        final_parts = []
        current_tokens = 0
        
        for layer in sorted_layers:
            budget = self.policy.layer_budgets.get(layer.name, 1000)
            if layer.tokens > budget:
                # 裁剪内容
                keep_chars = budget * 4
                content = layer.content[:keep_chars] + "... [TRUNCATED]"
                tokens = budget
                layer.truncated = True
                layer.truncation_reason = f"Exceeded layer budget {budget}"
                layer.tokens = tokens # 更新为实际 token
            else:
                content = layer.content
                tokens = layer.tokens
                
            if current_tokens + tokens <= self.policy.max_total_tokens:
                final_parts.append(f"### {layer.name.upper()} ###\n{content}")
                current_tokens += tokens
                layer.tokens = tokens # Update layer tokens to actual used
            else:
                # Try to fit partial content if not already truncated
                remaining = self.policy.max_total_tokens - current_tokens
                if remaining > 10: # Minimum useful chunk
                    keep_chars = remaining * 4
                    content = layer.content[:keep_chars] + "... [TRUNCATED]"
                    final_parts.append(f"### {layer.name.upper()} ###\n{content}")
                    layer.tokens = remaining
                    layer.truncated = True
                    layer.truncation_reason = "Global budget limit reached"
                    current_tokens += remaining
                else:
                    layer.truncated = True # 完全被丢弃也算 truncated
                    layer.truncation_reason = "Global budget exhausted"
                    layer.tokens = 0 # Discarded layer contributes 0 tokens
                break
        
        return "\n\n".join(final_parts)

    def get_usage(self) -> ContextManifest:
        total_tokens = sum(l.tokens for l in self._layers.values())
        layer_infos = [
            ContextLayerInfo(
                name=n, 
                tokens=l.tokens, 
                truncated=l.truncated,
                source=l.source,
                truncation_reason=l.truncation_reason
            )
            for n, l in self._layers.items()
        ]
        
        summary_parts = []
        for l in layer_infos:
            status = "TRUNCATED" if l.truncated else "FULL"
            summary_parts.append(f"{l.name}({l.tokens}t, {status})")
        
        return ContextManifest(
            layers=layer_infos,
            total_tokens=total_tokens,
            budget_limit=self.policy.max_total_tokens,
            compression_ratio=1.0, # 简化
            manifest_summary=", ".join(summary_parts)
        )
