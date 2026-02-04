"""
Phase 3B Week 6 Day 5-6: Simulation Orchestrator

核心目标：构建场控系统，管理 Sales Agent 和 User Simulator 的对抗训练。

核心功能：
1. 管理对话轮次
2. 防止死循环
3. 判定对话结束条件
4. 调用 Sales Coach 进行实时评估
5. 生成训练报告

实现日期: 2026-02-02
"""

import logging
import sys
import os
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState
from app.agents.simulation import CustomerPersonality, UserSimulator

logger = logging.getLogger(__name__)


class ConversationStatus(str, Enum):
    """对话状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_TURNS_REACHED = "max_turns_reached"
    DEADLOCK = "deadlock"


@dataclass
class Turn:
    """单轮对话"""
    turn_number: int
    sales_message: str
    customer_message: str
    sales_state: str
    customer_objection: bool
    customer_buying_signal: bool
    coach_feedback: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SimulationReport:
    """仿真训练报告"""
    session_id: str
    customer_personality: str
    total_turns: int
    final_status: ConversationStatus
    final_sales_state: str

    # 统计指标
    total_objections: int
    objections_resolved: int
    buying_signals: int

    # 评分
    average_score: float
    best_turn: Optional[int]
    worst_turn: Optional[int]

    # 详细记录
    turns: List[Turn]

    # 总结
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "customer_personality": self.customer_personality,
            "total_turns": self.total_turns,
            "final_status": self.final_status.value,
            "final_sales_state": self.final_sales_state,
            "total_objections": self.total_objections,
            "objections_resolved": self.objections_resolved,
            "buying_signals": self.buying_signals,
            "average_score": self.average_score,
            "best_turn": self.best_turn,
            "worst_turn": self.worst_turn,
            "turns": [
                {
                    "turn_number": t.turn_number,
                    "sales_message": t.sales_message,
                    "customer_message": t.customer_message,
                    "sales_state": t.sales_state,
                    "customer_objection": t.customer_objection,
                    "customer_buying_signal": t.customer_buying_signal,
                    "coach_score": t.coach_feedback.get("overall_score") if t.coach_feedback else None
                }
                for t in self.turns
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations
        }


class SimulationOrchestrator:
    """
    仿真训练场控

    核心功能：
    1. 管理 Sales Agent 和 User Simulator 的对话
    2. 控制对话轮次，防止死循环
    3. 判定对话结束条件
    4. 调用 Sales Coach 进行实时评估
    5. 生成训练报告
    """

    def __init__(
        self,
        sales_agent,
        sales_coach,
        max_turns: int = 20,
        deadlock_threshold: int = 5
    ):
        """
        初始化场控

        Args:
            sales_agent: Sales Agent 实例
            sales_coach: Sales Coach 实例
            max_turns: 最大对话轮次
            deadlock_threshold: 死锁检测阈值（连续多少轮无进展）
        """
        self.sales_agent = sales_agent
        self.sales_coach = sales_coach
        self.max_turns = max_turns
        self.deadlock_threshold = deadlock_threshold

        logger.info(
            f"SimulationOrchestrator initialized: "
            f"max_turns={max_turns}, deadlock_threshold={deadlock_threshold}"
        )

    async def run_simulation(
        self,
        session_id: str,
        customer_personality: CustomerPersonality,
        verbose: bool = True
    ) -> SimulationReport:
        """
        运行完整的仿真训练

        Args:
            session_id: 会话 ID
            customer_personality: 客户人格类型
            verbose: 是否打印详细信息

        Returns:
            SimulationReport: 训练报告
        """
        logger.info(
            f"Starting simulation: session={session_id}, "
            f"personality={customer_personality.value}"
        )

        # 1. 初始化
        user_simulator = UserSimulator(personality=customer_personality)
        turns: List[Turn] = []
        status = ConversationStatus.RUNNING

        # 2. 开场
        sales_message = "您好！我是XX银行的销售顾问，很高兴为您服务。请问您对信用卡有什么需求吗？"

        if verbose:
            print("\n" + "=" * 80)
            print(f"Simulation Started: {customer_personality.value}")
            print("=" * 80)

        # 3. 对话循环
        turn_number = 0
        no_progress_count = 0
        last_state = SalesState.OPENING

        while status == ConversationStatus.RUNNING and turn_number < self.max_turns:
            turn_number += 1

            if verbose:
                print(f"\n[Turn {turn_number}]")
                print(f"Sales: {sales_message}")

            # 3.1 User Simulator 响应
            customer_response = user_simulator.generate_response(
                sales_message,
                sales_state=last_state.value
            )

            customer_message = customer_response["content"]
            customer_objection = customer_response["objection"]
            customer_buying_signal = customer_response["buying_signal"]

            if verbose:
                print(f"Customer: {customer_message}")
                if customer_objection:
                    print("  [Objection Detected]")
                if customer_buying_signal:
                    print("  [Buying Signal Detected]")

            # 3.2 Sales Agent 响应
            agent_response = await self.sales_agent.process_message(
                session_id,
                customer_message
            )

            sales_message = agent_response.content
            current_state = SalesState(agent_response.current_state)

            if verbose:
                print(f"  State: {current_state.value}")

            # 3.3 Sales Coach 评估
            coach_feedback = None
            if self.sales_coach:
                feedback = self.sales_coach.evaluate_response(
                    sales_message=sales_message,
                    customer_message=customer_message,
                    current_stage=current_state
                )

                coach_feedback = {
                    "overall_score": feedback.overall_score,
                    "stage_alignment": feedback.stage_alignment,
                    "technique_used": feedback.technique_used,
                    "critique": feedback.critique,
                    "suggestion": feedback.suggestion,
                    "dimension_scores": feedback.dimension_scores
                }

                if verbose:
                    print(f"  Coach Score: {feedback.overall_score:.1f}/10")
                    print(f"  Technique: {feedback.technique_used}")

            # 3.4 记录本轮
            turn = Turn(
                turn_number=turn_number,
                sales_message=sales_message,
                customer_message=customer_message,
                sales_state=current_state.value,
                customer_objection=customer_objection,
                customer_buying_signal=customer_buying_signal,
                coach_feedback=coach_feedback
            )
            turns.append(turn)

            # 3.5 检查结束条件
            # 成功成交
            if customer_buying_signal and current_state == SalesState.CLOSING:
                status = ConversationStatus.COMPLETED
                if verbose:
                    print("\n[SUCCESS] Deal closed!")
                break

            # 客户明确拒绝
            if "不需要" in customer_message or "不感兴趣" in customer_message:
                if turn_number > 3:  # 至少尝试3轮
                    status = ConversationStatus.FAILED
                    if verbose:
                        print("\n[FAILED] Customer rejected")
                    break

            # 死锁检测
            if current_state == last_state:
                no_progress_count += 1
            else:
                no_progress_count = 0

            if no_progress_count >= self.deadlock_threshold:
                status = ConversationStatus.DEADLOCK
                if verbose:
                    print(f"\n[DEADLOCK] No progress for {self.deadlock_threshold} turns")
                break

            last_state = current_state

        # 4. 达到最大轮次
        if turn_number >= self.max_turns and status == ConversationStatus.RUNNING:
            status = ConversationStatus.MAX_TURNS_REACHED
            if verbose:
                print(f"\n[MAX TURNS] Reached {self.max_turns} turns")

        # 5. 生成报告
        report = self._generate_report(
            session_id=session_id,
            customer_personality=customer_personality,
            turns=turns,
            final_status=status,
            final_sales_state=current_state,
            user_simulator=user_simulator
        )

        if verbose:
            print("\n" + "=" * 80)
            print("Simulation Report")
            print("=" * 80)
            print(f"Status: {report.final_status.value}")
            print(f"Total Turns: {report.total_turns}")
            print(f"Average Score: {report.average_score:.1f}/10")
            print(f"Objections: {report.total_objections} (Resolved: {report.objections_resolved})")
            print(f"Buying Signals: {report.buying_signals}")
            print("\nStrengths:")
            for s in report.strengths:
                print(f"  - {s}")
            print("\nWeaknesses:")
            for w in report.weaknesses:
                print(f"  - {w}")
            print("\nRecommendations:")
            for r in report.recommendations:
                print(f"  - {r}")

        logger.info(
            f"Simulation completed: session={session_id}, "
            f"status={status.value}, turns={turn_number}"
        )

        return report

    def _generate_report(
        self,
        session_id: str,
        customer_personality: CustomerPersonality,
        turns: List[Turn],
        final_status: ConversationStatus,
        final_sales_state: SalesState,
        user_simulator: UserSimulator
    ) -> SimulationReport:
        """生成训练报告"""

        # 统计指标
        total_objections = sum(1 for t in turns if t.customer_objection)
        buying_signals = sum(1 for t in turns if t.customer_buying_signal)

        # 计算平均分
        scores = [
            t.coach_feedback["overall_score"]
            for t in turns
            if t.coach_feedback
        ]
        average_score = sum(scores) / len(scores) if scores else 0.0

        # 找出最好和最差的轮次
        best_turn = None
        worst_turn = None
        if scores:
            best_turn = scores.index(max(scores)) + 1
            worst_turn = scores.index(min(scores)) + 1

        # 分析优点和缺点
        strengths = []
        weaknesses = []
        recommendations = []

        # 根据最终状态给出建议
        if final_status == ConversationStatus.COMPLETED:
            strengths.append("成功完成销售，达成交易")
        elif final_status == ConversationStatus.FAILED:
            weaknesses.append("未能说服客户，需要改进异议处理")
            recommendations.append("加强 SPIN 提问，深入挖掘客户需求")
        elif final_status == ConversationStatus.DEADLOCK:
            weaknesses.append("对话陷入僵局，缺乏推进力")
            recommendations.append("注意状态转换，避免在同一阶段停留过久")
        elif final_status == ConversationStatus.MAX_TURNS_REACHED:
            weaknesses.append("对话过长，效率不高")
            recommendations.append("提高每轮对话的价值，更快推进到 Closing")

        # 根据平均分给出建议
        if average_score >= 8.0:
            strengths.append(f"整体表现优秀，平均分 {average_score:.1f}/10")
        elif average_score < 6.0:
            weaknesses.append(f"整体表现需要改进，平均分 {average_score:.1f}/10")
            recommendations.append("重点学习 SPIN 和 FAB 方法论")

        # 根据异议处理情况给出建议
        if total_objections > 0:
            objections_resolved = sum(
                1 for i, t in enumerate(turns)
                if t.customer_objection and i < len(turns) - 1 and not turns[i + 1].customer_objection
            )

            if objections_resolved / total_objections < 0.5:
                weaknesses.append("异议处理能力不足")
                recommendations.append("学习异议处理四步法：倾听、共情、澄清、解决")
        else:
            objections_resolved = 0

        return SimulationReport(
            session_id=session_id,
            customer_personality=customer_personality.value,
            total_turns=len(turns),
            final_status=final_status,
            final_sales_state=final_sales_state.value,
            total_objections=total_objections,
            objections_resolved=objections_resolved,
            buying_signals=buying_signals,
            average_score=average_score,
            best_turn=best_turn,
            worst_turn=worst_turn,
            turns=turns,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )

    async def run_batch_simulations(
        self,
        num_simulations: int = 10,
        personalities: Optional[List[CustomerPersonality]] = None,
        verbose: bool = False
    ) -> List[SimulationReport]:
        """
        批量运行仿真训练

        Args:
            num_simulations: 仿真次数
            personalities: 客户人格列表（如果为 None，则随机选择）
            verbose: 是否打印详细信息

        Returns:
            List[SimulationReport]: 训练报告列表
        """
        logger.info(f"Starting batch simulations: count={num_simulations}")

        if personalities is None:
            personalities = list(CustomerPersonality)

        reports = []

        for i in range(num_simulations):
            session_id = f"batch-sim-{i+1}"
            personality = personalities[i % len(personalities)]

            if verbose:
                print(f"\n{'=' * 80}")
                print(f"Simulation {i+1}/{num_simulations}")
                print(f"{'=' * 80}")

            report = await self.run_simulation(
                session_id=session_id,
                customer_personality=personality,
                verbose=verbose
            )

            reports.append(report)

        # 生成批量统计
        if verbose:
            self._print_batch_statistics(reports)

        return reports

    def _print_batch_statistics(self, reports: List[SimulationReport]):
        """打印批量统计"""
        print("\n" + "=" * 80)
        print("Batch Simulation Statistics")
        print("=" * 80)

        total = len(reports)
        completed = sum(1 for r in reports if r.final_status == ConversationStatus.COMPLETED)
        failed = sum(1 for r in reports if r.final_status == ConversationStatus.FAILED)
        deadlock = sum(1 for r in reports if r.final_status == ConversationStatus.DEADLOCK)
        max_turns = sum(1 for r in reports if r.final_status == ConversationStatus.MAX_TURNS_REACHED)

        print(f"\nTotal Simulations: {total}")
        print(f"Completed: {completed} ({completed/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"Deadlock: {deadlock} ({deadlock/total*100:.1f}%)")
        print(f"Max Turns: {max_turns} ({max_turns/total*100:.1f}%)")

        avg_score = sum(r.average_score for r in reports) / total
        avg_turns = sum(r.total_turns for r in reports) / total

        print(f"\nAverage Score: {avg_score:.1f}/10")
        print(f"Average Turns: {avg_turns:.1f}")

        # 按人格统计
        print("\nBy Personality:")
        personality_stats = {}
        for r in reports:
            p = r.customer_personality
            if p not in personality_stats:
                personality_stats[p] = {"count": 0, "completed": 0, "avg_score": 0}
            personality_stats[p]["count"] += 1
            if r.final_status == ConversationStatus.COMPLETED:
                personality_stats[p]["completed"] += 1
            personality_stats[p]["avg_score"] += r.average_score

        for p, stats in personality_stats.items():
            count = stats["count"]
            completed = stats["completed"]
            avg_score = stats["avg_score"] / count
            print(f"  {p}: {completed}/{count} completed, avg score {avg_score:.1f}/10")


# ============================================================================
# 测试和演示
# ============================================================================

async def demo_orchestrator():
    """演示场控系统"""
    print("=" * 80)
    print("Phase 3B Week 6 Day 5-6: Simulation Orchestrator Demo")
    print("=" * 80)

    # 导入必要的组件
    from app.agents.conversation import SalesConversationFSM, PromptManager

    # 创建 Sales Agent（简化版，用于演示）
    class MockSalesAgent:
        def __init__(self):
            self.fsm = SalesConversationFSM()
            self.prompt_manager = PromptManager()
            self.sessions = {}

        async def process_message(self, session_id, message):
            if session_id not in self.sessions:
                self.sessions[session_id] = self.fsm.create_context(session_id)

            context = self.sessions[session_id]

            # 简单的状态转换逻辑
            from app.agents.conversation import TransitionTrigger
            if context.current_state == SalesState.OPENING:
                self.fsm.transition_to(context, TransitionTrigger.RAPPORT_ESTABLISHED, "客户回应")

            # 生成响应（简化版）
            response_content = f"[{context.current_state.value}] 响应客户消息"

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
                current_state=context.current_state.value
            )

    # 创建 Sales Coach（简化版）
    class MockSalesCoach:
        def evaluate_response(self, sales_message, customer_message, current_stage):
            from dataclasses import dataclass

            @dataclass
            class Feedback:
                overall_score: float = 7.0
                stage_alignment: str = "Pass"
                technique_used: str = "Unknown"
                critique: str = "Good"
                suggestion: str = "Keep going"
                dimension_scores: dict = None

            return Feedback(dimension_scores={})

    # 创建场控
    sales_agent = MockSalesAgent()
    sales_coach = MockSalesCoach()

    orchestrator = SimulationOrchestrator(
        sales_agent=sales_agent,
        sales_coach=sales_coach,
        max_turns=10,
        deadlock_threshold=3
    )

    # 运行单次仿真
    print("\n[Single Simulation Test]")
    await orchestrator.run_simulation(
        session_id="demo-001",
        customer_personality=CustomerPersonality.INTERESTED,
        verbose=True
    )

    print("\n[OK] Demo completed successfully!")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行演示
    asyncio.run(demo_orchestrator())
