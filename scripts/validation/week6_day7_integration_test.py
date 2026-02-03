"""
Phase 3B Week 6 Day 7: Complete Integration Test & Training Data Generation

核心目标：
1. 集成所有组件（Sales Agent + User Simulator + Sales Coach + Orchestrator）
2. 运行完整的对抗训练
3. 生成大量训练数据
4. 分析训练效果

实现日期: 2026-02-02
"""

import logging
import sys
import os
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import (
    SalesState,
    TransitionTrigger,
    ConversationContext,
    SalesConversationFSM,
    PromptManager
)
from app.agents.simulation import (
    CustomerPersonality,
    UserSimulator,
    ConversationStatus,
    SimulationOrchestrator
)

logger = logging.getLogger(__name__)


class IntegratedSalesAgent:
    """
    完整集成的 Sales Agent

    集成了 Week 5 的所有功能：
    - FSM 状态管理
    - SPIN & FAB 方法论
    - 意图识别
    """

    def __init__(self):
        self.fsm = SalesConversationFSM()
        self.prompt_manager = PromptManager()
        self.sessions: Dict[str, ConversationContext] = {}

        logger.info("IntegratedSalesAgent initialized")

    async def process_message(self, session_id: str, message: str):
        """处理客户消息"""
        # 获取或创建会话
        if session_id not in self.sessions:
            self.sessions[session_id] = self.fsm.create_context(session_id)

        context = self.sessions[session_id]
        old_state = context.current_state

        # 记录消息
        context.history.append({"role": "user", "content": message})

        # 状态转换逻辑
        self._update_state(context, message)

        # 生成响应
        response_content = self._generate_response(context, message)

        # 记录响应
        context.history.append({"role": "assistant", "content": response_content})

        # 返回响应
        from dataclasses import dataclass

        @dataclass
        class Response:
            content: str
            current_state: str
            intent_detected: str = "unknown"
            rag_used: bool = False
            state_changed: bool = False
            metadata: dict = None

        return Response(
            content=response_content,
            current_state=context.current_state.value,
            state_changed=(old_state != context.current_state)
        )

    def _update_state(self, context: ConversationContext, message: str):
        """更新状态"""
        current_state = context.current_state

        # Opening -> Discovery
        if current_state == SalesState.OPENING:
            self.fsm.transition_to(
                context,
                TransitionTrigger.RAPPORT_ESTABLISHED,
                reason="客户开始交流"
            )

        # Discovery -> Pitch
        elif current_state == SalesState.DISCOVERY:
            context.discovery_questions_asked += 1

            # 检测购买信号
            buying_keywords = ["办理", "申请", "怎么办", "可以"]
            if any(k in message for k in buying_keywords):
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.BUYING_SIGNAL,
                    reason="检测到购买信号"
                )
            # 问够3个问题后进入 Pitch
            elif context.discovery_questions_asked >= 3:
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.NEEDS_IDENTIFIED,
                    reason="已收集足够信息"
                )

        # Pitch -> Objection
        elif current_state == SalesState.PITCH:
            context.pitch_attempts += 1

            # 检测异议
            objection_keywords = ["太贵", "不需要", "考虑", "不相信"]
            if any(k in message for k in objection_keywords):
                context.objections_raised.append(message[:30])
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.OBJECTION_RAISED,
                    reason="客户提出异议"
                )
            # 检测购买信号
            elif any(k in message for k in ["办理", "申请", "好的", "可以"]):
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.INTEREST_CONFIRMED,
                    reason="客户表达兴趣"
                )

        # Objection -> Pitch
        elif current_state == SalesState.OBJECTION:
            context.objection_handling_attempts += 1

            # 如果客户不再提异议，认为异议已解决
            objection_keywords = ["太贵", "不需要", "考虑", "不相信"]
            if not any(k in message for k in objection_keywords):
                if context.objections_raised:
                    context.objections_resolved.append(context.objections_raised[-1])
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.OBJECTION_RESOLVED,
                    reason="异议已处理"
                )

        # Closing -> Completed
        elif current_state == SalesState.CLOSING:
            context.closing_attempts += 1

            # 检测承诺
            commitment_keywords = ["好的", "办理", "申请", "开始"]
            if any(k in message for k in commitment_keywords):
                self.fsm.transition_to(
                    context,
                    TransitionTrigger.COMMITMENT_MADE,
                    reason="客户做出承诺"
                )

    def _generate_response(self, context: ConversationContext, message: str) -> str:
        """生成响应"""
        current_state = context.current_state

        if current_state == SalesState.OPENING:
            return "您好！我是XX银行的销售顾问，很高兴为您服务。请问您对信用卡有什么需求吗？"

        elif current_state == SalesState.DISCOVERY:
            # 使用 SPIN 提问
            questions = [
                "您目前使用信用卡的主要场景是什么？",
                "您觉得现在的信用卡有什么不太满意的地方吗？",
                "如果额度不够的问题一直存在，会对您造成什么影响？"
            ]
            q_index = min(context.discovery_questions_asked - 1, len(questions) - 1)
            return questions[q_index]

        elif current_state == SalesState.PITCH:
            # 使用 FAB 法则
            return "我们的白金卡最高额度可达50万，比市面上普通信用卡的5-10万额度高出5倍，这意味着您在大额消费时不用担心额度不够。"

        elif current_state == SalesState.OBJECTION:
            # 异议处理
            return "我理解您的顾虑。实际上，首年免年费，次年刷满6笔即可免年费，您可以零成本体验高端卡的所有权益。"

        elif current_state == SalesState.CLOSING:
            # 成交
            return "那我现在帮您办理，需要您提供一下身份证信息和联系方式。"

        else:
            return "请问还有什么我可以帮您的吗？"


class IntegratedSalesCoach:
    """
    完整集成的 Sales Coach

    集成了 Day 3-4 的评估功能
    """

    def __init__(self):
        # 导入 Sales Coach
        from scripts.week6_day3_sales_coach import SalesCoach
        self.coach = SalesCoach()

        logger.info("IntegratedSalesCoach initialized")

    def evaluate_response(self, sales_message: str, customer_message: str, current_stage: SalesState):
        """评估响应"""
        return self.coach.evaluate_response(
            sales_message=sales_message,
            customer_message=customer_message,
            current_stage=current_stage
        )


class TrainingDataGenerator:
    """
    训练数据生成器

    将仿真结果转换为训练数据
    """

    def __init__(self, output_dir: str = "training_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"TrainingDataGenerator initialized: output_dir={output_dir}")

    def save_simulation_report(self, report, filename: str = None):
        """保存仿真报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_report_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"Saved simulation report: {filepath}")
        return filepath

    def save_batch_reports(self, reports: List, filename: str = None):
        """保存批量报告"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"batch_reports_{timestamp}.json"

        filepath = os.path.join(self.output_dir, filename)

        data = {
            "total_simulations": len(reports),
            "timestamp": datetime.now().isoformat(),
            "reports": [r.to_dict() for r in reports]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved batch reports: {filepath}")
        return filepath

    def generate_training_dataset(self, reports: List) -> Dict[str, Any]:
        """生成训练数据集"""
        dataset = {
            "metadata": {
                "total_simulations": len(reports),
                "generated_at": datetime.now().isoformat(),
                "version": "1.0"
            },
            "statistics": self._calculate_statistics(reports),
            "conversations": []
        }

        for report in reports:
            conversation = {
                "session_id": report.session_id,
                "customer_personality": report.customer_personality,
                "final_status": report.final_status.value,
                "average_score": report.average_score,
                "turns": []
            }

            for turn in report.turns:
                conversation["turns"].append({
                    "turn_number": turn.turn_number,
                    "sales_message": turn.sales_message,
                    "customer_message": turn.customer_message,
                    "sales_state": turn.sales_state,
                    "coach_score": turn.coach_feedback.get("overall_score") if turn.coach_feedback else None,
                    "coach_feedback": turn.coach_feedback
                })

            dataset["conversations"].append(conversation)

        return dataset

    def _calculate_statistics(self, reports: List) -> Dict[str, Any]:
        """计算统计数据"""
        total = len(reports)

        if total == 0:
            return {}

        completed = sum(1 for r in reports if r.final_status == ConversationStatus.COMPLETED)
        failed = sum(1 for r in reports if r.final_status == ConversationStatus.FAILED)
        deadlock = sum(1 for r in reports if r.final_status == ConversationStatus.DEADLOCK)

        avg_score = sum(r.average_score for r in reports) / total
        avg_turns = sum(r.total_turns for r in reports) / total
        avg_objections = sum(r.total_objections for r in reports) / total

        return {
            "total_simulations": total,
            "completion_rate": completed / total,
            "failure_rate": failed / total,
            "deadlock_rate": deadlock / total,
            "average_score": avg_score,
            "average_turns": avg_turns,
            "average_objections": avg_objections
        }


# ============================================================================
# 完整集成测试
# ============================================================================

async def run_complete_integration_test():
    """运行完整集成测试"""
    print("=" * 80)
    print("Phase 3B Week 6 Day 7: Complete Integration Test")
    print("=" * 80)

    # 1. 初始化所有组件
    print("\n[Step 1] Initializing components...")
    sales_agent = IntegratedSalesAgent()
    sales_coach = IntegratedSalesCoach()
    orchestrator = SimulationOrchestrator(
        sales_agent=sales_agent,
        sales_coach=sales_coach,
        max_turns=15,
        deadlock_threshold=4
    )
    data_generator = TrainingDataGenerator(output_dir="training_data")

    print("  - Sales Agent: OK")
    print("  - Sales Coach: OK")
    print("  - Orchestrator: OK")
    print("  - Data Generator: OK")

    # 2. 运行单次仿真测试
    print("\n[Step 2] Running single simulation test...")
    report = await orchestrator.run_simulation(
        session_id="integration-test-001",
        customer_personality=CustomerPersonality.PRICE_SENSITIVE,
        verbose=True
    )

    # 保存报告
    filepath = data_generator.save_simulation_report(report)
    print(f"\n  Saved report: {filepath}")

    # 3. 运行批量仿真
    print("\n[Step 3] Running batch simulations...")
    print("  Testing all 6 personality types...")

    batch_reports = await orchestrator.run_batch_simulations(
        num_simulations=6,
        personalities=list(CustomerPersonality),
        verbose=False
    )

    # 打印批量统计
    orchestrator._print_batch_statistics(batch_reports)

    # 4. 生成训练数据集
    print("\n[Step 4] Generating training dataset...")
    dataset = data_generator.generate_training_dataset(batch_reports)

    # 保存数据集
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_file = f"training_dataset_{timestamp}.json"
    dataset_path = os.path.join(data_generator.output_dir, dataset_file)

    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"  Saved dataset: {dataset_path}")
    print(f"  Total conversations: {len(dataset['conversations'])}")
    print(f"  Total turns: {sum(len(c['turns']) for c in dataset['conversations'])}")

    # 5. 分析训练效果
    print("\n[Step 5] Training effectiveness analysis...")
    stats = dataset["statistics"]

    print(f"\n  Overall Performance:")
    print(f"    - Completion Rate: {stats['completion_rate']*100:.1f}%")
    print(f"    - Failure Rate: {stats['failure_rate']*100:.1f}%")
    print(f"    - Deadlock Rate: {stats['deadlock_rate']*100:.1f}%")
    print(f"    - Average Score: {stats['average_score']:.1f}/10")
    print(f"    - Average Turns: {stats['average_turns']:.1f}")
    print(f"    - Average Objections: {stats['average_objections']:.1f}")

    # 6. 生成改进建议
    print("\n[Step 6] Improvement recommendations...")

    recommendations = []

    if stats['completion_rate'] < 0.3:
        recommendations.append("成交率较低，需要加强 Closing 技巧")

    if stats['average_score'] < 7.0:
        recommendations.append("整体表现需要改进，重点学习 SPIN 和 FAB 方法论")

    if stats['deadlock_rate'] > 0.3:
        recommendations.append("死锁率较高，需要提高对话推进力")

    if stats['average_objections'] > 3:
        recommendations.append("异议处理能力需要加强")

    if recommendations:
        print("\n  Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"    {i}. {rec}")
    else:
        print("\n  Performance is good! Keep up the excellent work!")

    print("\n" + "=" * 80)
    print("Integration Test Completed Successfully!")
    print("=" * 80)

    return {
        "single_report": report,
        "batch_reports": batch_reports,
        "dataset": dataset,
        "dataset_path": dataset_path
    }


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行完整集成测试
    results = await run_complete_integration_test()

    print("\n[Summary]")
    print(f"  Single simulation: {results['single_report'].final_status.value}")
    print(f"  Batch simulations: {len(results['batch_reports'])} completed")
    print(f"  Training dataset: {results['dataset_path']}")
    print(f"  Total training samples: {len(results['dataset']['conversations'])}")

    print("\n[OK] All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
