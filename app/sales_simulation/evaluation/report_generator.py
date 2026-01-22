"""
报告生成器
生成评估报告
"""
import logging
import json
from typing import Dict, Any, List
from datetime import datetime

from app.sales_simulation.schemas.metrics import AggregatedMetrics
from app.sales_simulation.schemas.trajectory import Trajectory

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    @staticmethod
    def generate_json_report(
        run_id: str,
        metrics: AggregatedMetrics,
        trajectories: List[Trajectory],
    ) -> Dict[str, Any]:
        """生成 JSON 报告"""
        return {
            "run_id": run_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "num_trajectories": metrics.num_trajectories,
                "success_rate": metrics.success_rate,
                "avg_score": metrics.avg_score,
                "overall_quality": metrics.overall_quality,
            },
            "metrics": metrics.model_dump(),
            "recommendation": metrics.recommendation,
            "trajectories_summary": [
                {
                    "id": t.id,
                    "goal_achieved": t.goal_achieved,
                    "final_score": t.final_score,
                    "total_steps": t.total_steps,
                }
                for t in trajectories
            ],
        }
    
    @staticmethod
    def generate_markdown_report(
        run_id: str,
        metrics: AggregatedMetrics,
    ) -> str:
        """生成 Markdown 报告"""
        report = f"""# 销售模拟评估报告

## 基本信息
- **运行 ID**: {run_id}
- **生成时间**: {datetime.utcnow().isoformat()}
- **轨迹数量**: {metrics.num_trajectories}

## 核心指标
- **成功率**: {metrics.success_rate:.1%}
- **平均得分**: {metrics.avg_score:.2f}
- **平均步数**: {metrics.avg_steps:.1f}
- **整体质量**: {metrics.overall_quality:.2f}

## 一致性分析
- **得分标准差**: {metrics.consistency_metrics.score_std_dev:.3f}
- **稳定性评分**: {metrics.consistency_metrics.stability_score:.2f}

## 推荐建议
{metrics.recommendation}
"""
        return report





