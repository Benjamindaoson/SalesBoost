"""
MCP Learning Engine - 实时学习引擎

让MCP系统能够从每次使用中学习，持续自我优化。

核心能力：
1. 工具性能追踪
2. 工具组合效果分析
3. 成本-质量权衡学习
4. 自适应路由策略
5. 预测性规划

Author: Claude (Anthropic)
Version: 3.0
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionRecord:
    """工具执行记录"""
    tool_name: str
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    success: bool
    latency: float
    cost: float
    quality_score: float  # 0-1
    timestamp: float
    user_feedback: Optional[float] = None  # 用户反馈 0-1


@dataclass
class ToolPerformanceMetrics:
    """工具性能指标"""
    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    total_latency: float = 0.0
    total_cost: float = 0.0
    total_quality: float = 0.0
    context_performance: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_calls, 1)

    @property
    def avg_latency(self) -> float:
        return self.total_latency / max(self.total_calls, 1)

    @property
    def avg_cost(self) -> float:
        return self.total_cost / max(self.total_calls, 1)

    @property
    def avg_quality(self) -> float:
        return self.total_quality / max(self.total_calls, 1)


@dataclass
class ToolCombinationMetrics:
    """工具组合指标"""
    tools: Tuple[str, ...]
    execution_count: int = 0
    success_count: int = 0
    avg_total_cost: float = 0.0
    avg_total_latency: float = 0.0
    avg_quality: float = 0.0
    user_satisfaction: float = 0.0


class MCPLearningEngine:
    """
    MCP学习引擎

    从每次工具使用中学习，持续优化系统性能。

    核心功能：
    1. 追踪工具性能
    2. 分析工具组合效果
    3. 学习上下文-工具映射
    4. 优化成本-质量权衡
    5. 预测最佳工具选择

    Usage:
        engine = MCPLearningEngine()

        # 记录执行
        engine.record_execution(
            tool_name="knowledge_retriever",
            parameters={"query": "..."},
            context={"industry": "SaaS"},
            success=True,
            latency=1.2,
            cost=0.01,
            quality_score=0.9
        )

        # 获取推荐
        recommendations = engine.recommend_tools(
            intent="research customer",
            context={"industry": "SaaS"}
        )

        # 预测成本
        predicted_cost = engine.predict_cost(
            tools=["tool1", "tool2"],
            context={"industry": "SaaS"}
        )
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        min_samples_for_learning: int = 10,
    ):
        """
        Initialize learning engine

        Args:
            learning_rate: Learning rate for updates
            min_samples_for_learning: Minimum samples before learning
        """
        self.learning_rate = learning_rate
        self.min_samples = min_samples_for_learning

        # Performance tracking
        self.tool_metrics: Dict[str, ToolPerformanceMetrics] = {}
        self.combination_metrics: Dict[Tuple[str, ...], ToolCombinationMetrics] = {}
        self.execution_history: List[ToolExecutionRecord] = []

        # Learned patterns
        self.context_tool_scores: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.tool_synergies: Dict[Tuple[str, str], float] = {}  # Tool pair synergies

        logger.info("Learning Engine initialized")

    def record_execution(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Dict[str, Any],
        success: bool,
        latency: float,
        cost: float,
        quality_score: float,
        user_feedback: Optional[float] = None,
    ):
        """
        记录工具执行

        Args:
            tool_name: Tool name
            parameters: Tool parameters
            context: Execution context
            success: Whether execution succeeded
            latency: Execution latency
            cost: Execution cost
            quality_score: Quality score (0-1)
            user_feedback: Optional user feedback (0-1)
        """
        # Create record
        record = ToolExecutionRecord(
            tool_name=tool_name,
            parameters=parameters,
            context=context,
            success=success,
            latency=latency,
            cost=cost,
            quality_score=quality_score,
            timestamp=time.time(),
            user_feedback=user_feedback,
        )

        self.execution_history.append(record)

        # Update metrics
        self._update_tool_metrics(record)
        self._update_context_patterns(record)

        # Trigger learning if enough samples
        if len(self.execution_history) % self.min_samples == 0:
            self._learn_from_history()

        logger.debug(f"Recorded execution: {tool_name} (success={success}, quality={quality_score:.2f})")

    def record_combination(
        self,
        tools: List[str],
        success: bool,
        total_cost: float,
        total_latency: float,
        quality_score: float,
        user_satisfaction: Optional[float] = None,
    ):
        """
        记录工具组合执行

        Args:
            tools: List of tools used
            success: Whether combination succeeded
            total_cost: Total cost
            total_latency: Total latency
            quality_score: Quality score
            user_satisfaction: User satisfaction score
        """
        tools_tuple = tuple(sorted(tools))

        if tools_tuple not in self.combination_metrics:
            self.combination_metrics[tools_tuple] = ToolCombinationMetrics(tools=tools_tuple)

        metrics = self.combination_metrics[tools_tuple]
        metrics.execution_count += 1

        if success:
            metrics.success_count += 1

        # Update averages (exponential moving average)
        alpha = self.learning_rate
        metrics.avg_total_cost = alpha * total_cost + (1 - alpha) * metrics.avg_total_cost
        metrics.avg_total_latency = alpha * total_latency + (1 - alpha) * metrics.avg_total_latency
        metrics.avg_quality = alpha * quality_score + (1 - alpha) * metrics.avg_quality

        if user_satisfaction is not None:
            metrics.user_satisfaction = alpha * user_satisfaction + (1 - alpha) * metrics.user_satisfaction

        logger.debug(f"Recorded combination: {tools} (quality={quality_score:.2f})")

    def _update_tool_metrics(self, record: ToolExecutionRecord):
        """Update tool performance metrics"""
        tool_name = record.tool_name

        if tool_name not in self.tool_metrics:
            self.tool_metrics[tool_name] = ToolPerformanceMetrics(tool_name=tool_name)

        metrics = self.tool_metrics[tool_name]
        metrics.total_calls += 1

        if record.success:
            metrics.success_count += 1

        metrics.total_latency += record.latency
        metrics.total_cost += record.cost
        metrics.total_quality += record.quality_score

    def _update_context_patterns(self, record: ToolExecutionRecord):
        """Update context-tool performance patterns"""
        tool_name = record.tool_name

        # Extract context features
        for key, value in record.context.items():
            if isinstance(value, str):
                context_key = f"{key}:{value}"

                # Update score (exponential moving average)
                current_score = self.context_tool_scores[context_key][tool_name]
                new_score = record.quality_score if record.success else 0.0

                self.context_tool_scores[context_key][tool_name] = (
                    self.learning_rate * new_score + (1 - self.learning_rate) * current_score
                )

    def _learn_from_history(self):
        """Learn patterns from execution history"""
        logger.info("Learning from execution history...")

        # Learn tool synergies
        self._learn_tool_synergies()

        # Learn cost-quality tradeoffs
        self._learn_cost_quality_tradeoffs()

        logger.info("Learning complete")

    def _learn_tool_synergies(self):
        """Learn which tools work well together"""
        # Group executions by time window
        window_size = 60.0  # 60 seconds

        recent_executions = [r for r in self.execution_history[-100:]]  # Last 100

        # Find tool pairs that often appear together
        tool_pairs = defaultdict(list)

        for i, record1 in enumerate(recent_executions):
            for record2 in recent_executions[i + 1:]:
                if abs(record1.timestamp - record2.timestamp) < window_size:
                    pair = tuple(sorted([record1.tool_name, record2.tool_name]))
                    combined_quality = (record1.quality_score + record2.quality_score) / 2
                    tool_pairs[pair].append(combined_quality)

        # Calculate synergy scores
        for pair, qualities in tool_pairs.items():
            if len(qualities) >= 3:  # Need at least 3 samples
                avg_quality = np.mean(qualities)
                self.tool_synergies[pair] = avg_quality

    def _learn_cost_quality_tradeoffs(self):
        """Learn optimal cost-quality tradeoffs"""
        # Analyze cost vs quality for each tool
        for tool_name, metrics in self.tool_metrics.items():
            if metrics.total_calls >= self.min_samples:
                # Calculate efficiency score
                efficiency = metrics.avg_quality / max(metrics.avg_cost, 0.001)
                logger.debug(f"Tool {tool_name} efficiency: {efficiency:.2f}")

    def recommend_tools(
        self,
        intent: str,
        context: Dict[str, Any],
        max_cost: Optional[float] = None,
        min_quality: Optional[float] = None,
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """
        推荐最佳工具

        Args:
            intent: User intent
            context: Execution context
            max_cost: Maximum cost constraint
            min_quality: Minimum quality constraint
            top_k: Number of recommendations

        Returns:
            List of (tool_name, score) tuples
        """
        tool_scores = {}

        for tool_name, metrics in self.tool_metrics.items():
            if metrics.total_calls < 3:  # Need minimum samples
                continue

            # Base score from historical performance
            base_score = metrics.avg_quality * metrics.success_rate

            # Context bonus
            context_bonus = 0.0
            for key, value in context.items():
                if isinstance(value, str):
                    context_key = f"{key}:{value}"
                    context_bonus += self.context_tool_scores[context_key].get(tool_name, 0.0)

            # Cost penalty
            cost_penalty = 0.0
            if max_cost and metrics.avg_cost > max_cost:
                cost_penalty = -0.5

            # Quality filter
            if min_quality and metrics.avg_quality < min_quality:
                continue

            # Combined score
            score = base_score + context_bonus * 0.3 + cost_penalty
            tool_scores[tool_name] = score

        # Sort and return top-k
        sorted_tools = sorted(tool_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_tools[:top_k]

    def recommend_tool_combination(
        self,
        intent: str,
        context: Dict[str, Any],
        max_cost: Optional[float] = None,
    ) -> List[str]:
        """
        推荐最佳工具组合

        Args:
            intent: User intent
            context: Execution context
            max_cost: Maximum cost constraint

        Returns:
            List of recommended tools
        """
        # Get individual tool recommendations
        tool_recommendations = self.recommend_tools(intent, context, max_cost, top_k=10)

        if not tool_recommendations:
            return []

        # Consider synergies
        best_combination = []
        best_score = 0.0

        # Try different combinations (greedy approach)
        available_tools = [t[0] for t in tool_recommendations]

        for i, tool1 in enumerate(available_tools[:5]):  # Limit search
            for tool2 in available_tools[i + 1:5]:
                pair = tuple(sorted([tool1, tool2]))
                synergy = self.tool_synergies.get(pair, 0.0)

                # Calculate combination score
                tool1_score = dict(tool_recommendations)[tool1]
                tool2_score = dict(tool_recommendations)[tool2]
                combination_score = tool1_score + tool2_score + synergy

                if combination_score > best_score:
                    best_score = combination_score
                    best_combination = [tool1, tool2]

        return best_combination if best_combination else [tool_recommendations[0][0]]

    def predict_cost(
        self,
        tools: List[str],
        context: Dict[str, Any],
    ) -> float:
        """
        预测工具组合的成本

        Args:
            tools: List of tools
            context: Execution context

        Returns:
            Predicted cost
        """
        total_cost = 0.0

        for tool_name in tools:
            if tool_name in self.tool_metrics:
                metrics = self.tool_metrics[tool_name]
                total_cost += metrics.avg_cost
            else:
                # Default estimate
                total_cost += 0.01

        return total_cost

    def predict_quality(
        self,
        tools: List[str],
        context: Dict[str, Any],
    ) -> float:
        """
        预测工具组合的质量

        Args:
            tools: List of tools
            context: Execution context

        Returns:
            Predicted quality (0-1)
        """
        if not tools:
            return 0.0

        qualities = []

        for tool_name in tools:
            if tool_name in self.tool_metrics:
                metrics = self.tool_metrics[tool_name]
                base_quality = metrics.avg_quality

                # Context adjustment
                context_bonus = 0.0
                for key, value in context.items():
                    if isinstance(value, str):
                        context_key = f"{key}:{value}"
                        context_bonus += self.context_tool_scores[context_key].get(tool_name, 0.0)

                adjusted_quality = min(base_quality + context_bonus * 0.1, 1.0)
                qualities.append(adjusted_quality)
            else:
                qualities.append(0.5)  # Default

        # Consider synergies
        if len(tools) >= 2:
            for i, tool1 in enumerate(tools):
                for tool2 in tools[i + 1:]:
                    pair = tuple(sorted([tool1, tool2]))
                    synergy = self.tool_synergies.get(pair, 0.0)
                    qualities.append(synergy)

        return np.mean(qualities)

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "total_executions": len(self.execution_history),
            "tools_tracked": len(self.tool_metrics),
            "combinations_tracked": len(self.combination_metrics),
            "tool_performance": {},
            "best_combinations": [],
            "learned_patterns": {
                "context_patterns": len(self.context_tool_scores),
                "tool_synergies": len(self.tool_synergies),
            },
        }

        # Tool performance
        for tool_name, metrics in self.tool_metrics.items():
            report["tool_performance"][tool_name] = {
                "calls": metrics.total_calls,
                "success_rate": metrics.success_rate,
                "avg_latency": metrics.avg_latency,
                "avg_cost": metrics.avg_cost,
                "avg_quality": metrics.avg_quality,
            }

        # Best combinations
        sorted_combinations = sorted(
            self.combination_metrics.items(),
            key=lambda x: x[1].avg_quality * x[1].success_count,
            reverse=True,
        )

        for tools, metrics in sorted_combinations[:5]:
            report["best_combinations"].append({
                "tools": list(tools),
                "executions": metrics.execution_count,
                "success_rate": metrics.success_count / max(metrics.execution_count, 1),
                "avg_quality": metrics.avg_quality,
                "avg_cost": metrics.avg_total_cost,
            })

        return report

    def export_knowledge(self, filepath: str):
        """导出学习到的知识"""
        knowledge = {
            "tool_metrics": {
                name: {
                    "total_calls": m.total_calls,
                    "success_rate": m.success_rate,
                    "avg_latency": m.avg_latency,
                    "avg_cost": m.avg_cost,
                    "avg_quality": m.avg_quality,
                }
                for name, m in self.tool_metrics.items()
            },
            "context_tool_scores": dict(self.context_tool_scores),
            "tool_synergies": {str(k): v for k, v in self.tool_synergies.items()},
        }

        with open(filepath, "w") as f:
            json.dump(knowledge, f, indent=2)

        logger.info(f"Knowledge exported to {filepath}")

    def import_knowledge(self, filepath: str):
        """导入学习到的知识"""
        with open(filepath, "r") as f:
            knowledge = json.load(f)

        # Import metrics
        for name, data in knowledge.get("tool_metrics", {}).items():
            if name not in self.tool_metrics:
                self.tool_metrics[name] = ToolPerformanceMetrics(tool_name=name)

        # Import patterns
        self.context_tool_scores.update(knowledge.get("context_tool_scores", {}))

        logger.info(f"Knowledge imported from {filepath}")
