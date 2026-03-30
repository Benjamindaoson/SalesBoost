"""
RAGAS 持续评估和监控系统

功能：
1. 持续评估 RAG 质量
2. 自动生成报告
3. 性能追踪
4. 告警系统
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


from ..evaluation.ragas_evaluator import (
    RAGASBatchEvaluator,
    RAGASEvaluationInput,
    RAGASEvaluator,
)

logger = logging.getLogger(__name__)


class RAGASMonitor:
    """
    RAGAS 持续监控系统

    功能：
    1. 定期评估
    2. 性能追踪
    3. 告警
    4. 报告生成
    """

    def __init__(
        self,
        evaluator: RAGASEvaluator,
        storage_path: str = "./monitoring/ragas",
        alert_threshold: float = 0.6,
    ):
        """
        初始化监控系统

        Args:
            evaluator: RAGAS 评估器
            storage_path: 存储路径
            alert_threshold: 告警阈值
        """
        self.evaluator = evaluator
        self.batch_evaluator = RAGASBatchEvaluator(evaluator)
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.alert_threshold = alert_threshold

        # 历史数据
        self.history: List[Dict[str, Any]] = []
        self._load_history()

    def _load_history(self):
        """加载历史数据"""
        history_file = self.storage_path / "history.json"

        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    self.history = json.load(f)
                logger.info(f"Loaded {len(self.history)} historical evaluations")
            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                self.history = []

    def _save_history(self):
        """保存历史数据"""
        history_file = self.storage_path / "history.json"

        try:
            with open(history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    async def evaluate_and_record(
        self, test_cases: List[RAGASEvaluationInput], metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        评估并记录结果

        Args:
            test_cases: 测试用例
            metadata: 元数据

        Returns:
            评估结果
        """
        logger.info(f"Evaluating {len(test_cases)} test cases")

        # 评估
        results = await self.batch_evaluator.evaluate_batch(test_cases)

        # 添加时间戳和元数据
        record = {
            "timestamp": datetime.now().isoformat(),
            "num_test_cases": len(test_cases),
            "metrics": results["metrics"],
            "metadata": metadata or {},
        }

        # 记录
        self.history.append(record)
        self._save_history()

        # 检查告警
        await self._check_alerts(record)

        # 生成报告
        await self._generate_report(record)

        return results

    async def _check_alerts(self, record: Dict[str, Any]):
        """检查告警"""
        metrics = record["metrics"]

        alerts = []

        # 检查各项指标
        for metric_name, metric_data in metrics.items():
            mean_value = metric_data["mean"]

            if mean_value < self.alert_threshold:
                alerts.append(
                    {
                        "metric": metric_name,
                        "value": mean_value,
                        "threshold": self.alert_threshold,
                        "severity": "high" if mean_value < 0.5 else "medium",
                    }
                )

        if alerts:
            logger.warning(f"⚠️  Quality alerts triggered: {len(alerts)} issues")

            for alert in alerts:
                logger.warning(
                    f"  - {alert['metric']}: {alert['value']:.3f} < {alert['threshold']:.3f}"
                )

            # 保存告警
            await self._save_alert(record, alerts)

    async def _save_alert(self, record: Dict[str, Any], alerts: List[Dict]):
        """保存告警"""
        alert_file = self.storage_path / f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(alert_file, "w") as f:
                json.dump(
                    {
                        "timestamp": record["timestamp"],
                        "alerts": alerts,
                        "metrics": record["metrics"],
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")

    async def _generate_report(self, record: Dict[str, Any]):
        """生成报告"""
        report_file = self.storage_path / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        try:
            report = self._format_report(record)

            with open(report_file, "w") as f:
                f.write(report)

            logger.info(f"Report generated: {report_file}")

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")

    def _format_report(self, record: Dict[str, Any]) -> str:
        """格式化报告"""
        metrics = record["metrics"]

        report = f"""# RAGAS 评估报告

**时间**: {record['timestamp']}
**测试用例数**: {record['num_test_cases']}

## 指标概览

| 指标 | 平均值 | 标准差 | 最小值 | 最大值 | 状态 |
|------|--------|--------|--------|--------|------|
"""

        for metric_name, metric_data in metrics.items():
            mean = metric_data["mean"]
            std = metric_data["std"]
            min_val = metric_data["min"]
            max_val = metric_data["max"]

            status = "✅" if mean >= self.alert_threshold else "⚠️"

            report += f"| {metric_name} | {mean:.3f} | {std:.3f} | {min_val:.3f} | {max_val:.3f} | {status} |\n"

        # 添加趋势分析
        if len(self.history) > 1:
            report += "\n## 趋势分析\n\n"
            report += self._format_trend_analysis()

        # 添加建议
        report += "\n## 改进建议\n\n"
        report += self._format_recommendations(metrics)

        return report

    def _format_trend_analysis(self) -> str:
        """格式化趋势分析"""
        if len(self.history) < 2:
            return "数据不足，无法进行趋势分析。\n"

        # 获取最近 10 次评估
        recent = self.history[-10:]

        # 计算趋势
        trends = {}

        for metric_name in ["context_precision", "context_recall", "faithfulness", "answer_relevance"]:
            values = [r["metrics"][metric_name]["mean"] for r in recent]

            if len(values) >= 2:
                # 简单线性趋势
                trend = values[-1] - values[0]
                trends[metric_name] = trend

        # 格式化
        text = ""

        for metric_name, trend in trends.items():
            if trend > 0.05:
                text += f"- **{metric_name}**: 📈 上升趋势 (+{trend:.3f})\n"
            elif trend < -0.05:
                text += f"- **{metric_name}**: 📉 下降趋势 ({trend:.3f})\n"
            else:
                text += f"- **{metric_name}**: ➡️ 稳定\n"

        return text

    def _format_recommendations(self, metrics: Dict[str, Any]) -> str:
        """格式化改进建议"""
        recommendations = []

        # Context Precision
        if metrics["context_precision"]["mean"] < 0.7:
            recommendations.append(
                "- **提升检索精度**: 考虑使用 HyDE 或改进查询重写"
            )

        # Context Recall
        if metrics["context_recall"]["mean"] < 0.7:
            recommendations.append(
                "- **提升检索召回**: 增加 top_k 或使用混合检索"
            )

        # Faithfulness
        if metrics["faithfulness"]["mean"] < 0.8:
            recommendations.append(
                "- **减少幻觉**: 使用 Self-RAG 或加强提示词约束"
            )

        # Answer Relevance
        if metrics["answer_relevance"]["mean"] < 0.7:
            recommendations.append(
                "- **提升答案相关性**: 优化生成提示词或使用更强的模型"
            )

        if not recommendations:
            recommendations.append("- ✅ 所有指标表现良好，继续保持！")

        return "\n".join(recommendations)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        if not self.history:
            return {"error": "No data available"}

        # 最近 30 天数据
        cutoff = datetime.now() - timedelta(days=30)
        recent = [
            r
            for r in self.history
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not recent:
            recent = self.history[-10:]  # 至少显示最近 10 次

        # 提取时间序列数据
        timestamps = [r["timestamp"] for r in recent]

        metrics_over_time = {}

        for metric_name in ["context_precision", "context_recall", "faithfulness", "answer_relevance", "overall_score"]:
            metrics_over_time[metric_name] = [
                r["metrics"][metric_name]["mean"] for r in recent
            ]

        # 当前状态
        latest = recent[-1]

        return {
            "timestamps": timestamps,
            "metrics_over_time": metrics_over_time,
            "latest_metrics": latest["metrics"],
            "total_evaluations": len(self.history),
            "recent_evaluations": len(recent),
        }


class RAGASScheduler:
    """
    RAGAS 定时评估调度器

    功能：
    1. 定时评估
    2. 自动采样
    3. 持续监控
    """

    def __init__(
        self,
        monitor: RAGASMonitor,
        interval_hours: int = 24,
    ):
        """
        初始化调度器

        Args:
            monitor: RAGAS 监控器
            interval_hours: 评估间隔（小时）
        """
        self.monitor = monitor
        self.interval_hours = interval_hours
        self.running = False

    async def start(self):
        """启动调度器"""
        self.running = True

        logger.info(f"RAGAS scheduler started (interval: {self.interval_hours}h)")

        while self.running:
            try:
                # 执行评估
                await self._run_evaluation()

                # 等待下次评估
                await asyncio.sleep(self.interval_hours * 3600)

            except Exception as e:
                logger.error(f"Evaluation failed: {e}")
                await asyncio.sleep(3600)  # 错误后等待 1 小时

    async def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("RAGAS scheduler stopped")

    async def _run_evaluation(self):
        """运行评估"""
        logger.info("Running scheduled RAGAS evaluation")

        # 这里需要从生产环境采样测试用例
        # 实际实现中，应该从日志或数据库中采样真实的查询和答案

        # 示例：从日志采样
        test_cases = await self._sample_test_cases()

        if test_cases:
            await self.monitor.evaluate_and_record(
                test_cases,
                metadata={"source": "scheduled", "interval_hours": self.interval_hours},
            )

    async def _sample_test_cases(self) -> List[RAGASEvaluationInput]:
        """从生产环境采样测试用例"""
        # TODO: 实现从日志/数据库采样
        # 这里返回空列表作为示例
        return []
