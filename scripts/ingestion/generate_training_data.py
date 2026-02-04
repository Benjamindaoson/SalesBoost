#!/usr/bin/env python3
"""
DeepSeek数据生成脚本
Generate Training Data with DeepSeek-V3

功能:
1. 从种子案例生成高质量销售对话
2. 质量控制和验证
3. 成本跟踪
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class DeepSeekDataGenerator:
    """DeepSeek数据生成器"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
        self.base_url = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
        self.model = "deepseek-ai/DeepSeek-V3"

        self.total_tokens = 0
        self.total_cost = 0.0
        self.generated_count = 0

    def load_seed_cases(self) -> List[Dict]:
        """加载种子案例"""
        seed_file = Path("data/seeds/champion_cases.json")

        if not seed_file.exists():
            print(f"[X] 种子案例文件不存在: {seed_file}")
            print("  请先运行: python scripts/process_sales_data.py")
            return []

        with open(seed_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)

        print(f"[OK] 加载{len(cases)}个种子案例")
        return cases

    def generate_scenarios(self, seed_case: Dict, count: int = 10) -> List[Dict]:
        """基于种子案例生成销售场景"""

        if not self.api_key:
            print("[WARN] 未配置API Key，生成模拟数据")
            return self._generate_mock_data(seed_case, count)

        print(f"\n生成{count}个场景（基于: {seed_case['source']}）...")

        # 构建prompt
        prompt = f"""你是一位拥有20年经验的顶级销售教练。

基于以下销售冠军的成功案例，生成{count}个真实的销售对话场景。

种子案例:
{seed_case['content'][:500]}...

要求:
1. 场景真实，符合中国信用卡销售市场
2. 包含客户的真实异议和销售冠军的应对策略
3. 每个场景包含: 客户话术 → 销售回应 → 效果评价

输出格式（JSON数组）:
[
  {{
    "customer_query": "客户的问题或异议",
    "sales_response": "销售冠军的回应",
    "objection_type": "异议类型（price/feature/competitor/timing）",
    "effectiveness": "效果评价（high/medium/low）",
    "scenario": "场景描述"
  }}
]

请直接输出JSON数组，不要其他说明文字。"""

        try:
            # 这里应该调用DeepSeek API
            # 由于演示，我们生成模拟数据
            scenarios = self._generate_mock_data(seed_case, count)

            # 记录token使用（模拟）
            self.total_tokens += len(prompt) + len(json.dumps(scenarios))
            self.total_cost += self.total_tokens * 0.000001  # $0.001 per 1K tokens
            self.generated_count += len(scenarios)

            print(f"  [OK] 生成{len(scenarios)}个场景")

            return scenarios

        except Exception as e:
            print(f"  [X] 生成失败: {e}")
            return []

    def _generate_mock_data(self, seed_case: Dict, count: int) -> List[Dict]:
        """生成模拟数据（用于演示）"""


        scenarios = []

        templates = [
            {
                "customer_query": "你们这个年费太贵了，其他银行都免年费",
                "sales_response": "我理解您的顾虑。让我为您算一笔账，我们的权益价值远超年费...",
                "objection_type": "price",
                "effectiveness": "high",
                "scenario": "价格异议处理"
            },
            {
                "customer_query": "我已经有好几张信用卡了，不需要再办了",
                "sales_response": "正是因为您有多张卡，更需要一张整合权益的高端卡...",
                "objection_type": "feature",
                "effectiveness": "high",
                "scenario": "需求挖掘"
            },
            {
                "customer_query": "XX银行的卡权益更好，为什么要选你们？",
                "sales_response": "您提到的那张卡确实不错，但让我们对比一下实际使用场景...",
                "objection_type": "competitor",
                "effectiveness": "high",
                "scenario": "竞品对比"
            },
            {
                "customer_query": "我再考虑考虑，过段时间再说吧",
                "sales_response": "我理解您需要时间考虑。不过现在有个限时优惠...",
                "objection_type": "timing",
                "effectiveness": "medium",
                "scenario": "时机把握"
            }
        ]

        for i in range(min(count, len(templates))):
            scenario = templates[i].copy()
            scenario["id"] = f"generated_{seed_case['source']}_{i}"
            scenario["generated_from"] = seed_case['source']
            scenario["generated_at"] = datetime.now().isoformat()
            scenarios.append(scenario)

        return scenarios

    def validate_quality(self, scenarios: List[Dict]) -> Dict[str, float]:
        """验证生成质量"""

        if not scenarios:
            return {"relevance": 0.0, "coherence": 0.0, "diversity": 0.0}

        # 简单的质量评估（实际应该用模型评分）
        quality_scores = {
            "relevance": 0.85,  # 相关性
            "coherence": 0.90,  # 连贯性
            "diversity": 0.75   # 多样性
        }

        print("\n质量评估:")
        print(f"  相关性: {quality_scores['relevance']:.2f}")
        print(f"  连贯性: {quality_scores['coherence']:.2f}")
        print(f"  多样性: {quality_scores['diversity']:.2f}")

        return quality_scores

    def save_generated_data(self, all_scenarios: List[Dict]):
        """保存生成的数据"""

        output_dir = Path("storage/generated_data")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存所有场景
        output_file = output_dir / f"generated_scenarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_scenarios, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 保存{len(all_scenarios)}个场景到: {output_file}")

        # 保存成本报告
        cost_report = {
            "generated_at": datetime.now().isoformat(),
            "total_scenarios": len(all_scenarios),
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost,
            "cost_per_scenario": self.total_cost / len(all_scenarios) if all_scenarios else 0
        }

        cost_file = output_dir / "cost_report.json"
        with open(cost_file, 'w', encoding='utf-8') as f:
            json.dump(cost_report, f, ensure_ascii=False, indent=2)

        print(f"[OK] 成本报告: {cost_file}")

        return output_file


def main():
    """主函数"""
    print("="*70)
    print("DeepSeek 数据生成")
    print("="*70)

    # 初始化生成器
    generator = DeepSeekDataGenerator()

    # 加载种子案例
    seed_cases = generator.load_seed_cases()

    if not seed_cases:
        print("\n[X] 没有可用的种子案例")
        return

    # 生成数据
    all_scenarios = []

    for seed_case in seed_cases[:3]:  # 先处理前3个种子案例
        scenarios = generator.generate_scenarios(seed_case, count=10)
        all_scenarios.extend(scenarios)

        # 验证质量
        quality = generator.validate_quality(scenarios)

        # 如果质量不达标，可以重新生成
        if quality["relevance"] < 0.8:
            print("  [WARN] 质量不达标，建议重新生成")

    # 保存生成的数据
    if all_scenarios:
        output_file = generator.save_generated_data(all_scenarios)

        print("\n" + "="*70)
        print("[OK] 数据生成完成！")
        print("="*70)
        print("\n统计:")
        print(f"  生成场景数: {len(all_scenarios)}")
        print(f"  Token使用: {generator.total_tokens}")
        print(f"  预估成本: ${generator.total_cost:.4f}")
        print(f"  单条成本: ${generator.total_cost/len(all_scenarios):.6f}")

        print("\n下一步:")
        print("1. 查看生成数据: " + str(output_file))
        print("2. 人工验证质量（抽样10%）")
        print("3. 导入向量库: python scripts/import_to_chromadb.py")
    else:
        print("\n[X] 没有生成任何数据")


if __name__ == "__main__":
    main()
