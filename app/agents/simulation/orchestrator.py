"""
Simulation Orchestrator

Phase 3B Week 6 Day 5-6 交付物

集成到 SalesBoost 的仿真训练场控模块
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

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
    total_objections: int
    objections_resolved: int
    buying_signals: int
    average_score: float
    best_turn: Optional[int]
    worst_turn: Optional[int]
    turns: List[Turn]
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
    """仿真训练场控"""

    def __init__(
        self,
        sales_agent,
        sales_coach,
        max_turns: int = 20,
        deadlock_threshold: int = 5
    ):
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
        """运行完整的仿真训练"""
        logger.info(
            f"Starting simulation: session={session_id}, "
            f"personality={customer_personality.value}"
        )

        user_simulator = UserSimulator(personality=customer_personality)
        turns: List[Turn] = []
        status = ConversationStatus.RUNNING

        sales_message = "您好！我是XX银行的销售顾问，很高兴为您服务。请问您对信用卡有什么需求吗？"

        if verbose:
            print("\n" + "=" * 80)
            print(f"Simulation Started: {customer_personality.value}")
            print("=" * 80)

        turn_number = 0
        no_progress_count = 0
        last_state = SalesState.OPENING

        while status == ConversationStatus.RUNNING and turn_number < self.max_turns:
            turn_number += 1

            if verbose:
                print(f"\n[Turn {turn_number}]")
                print(f"Sales: {sales_message}")

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

            agent_response = await self.sales_agent.process_message(
                session_id,
                customer_message
            )

            sales_message = agent_response.content
            current_state = SalesState(agent_response.current_state)

            if verbose:
                print(f"  State: {current_state.value}")

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

            if customer_buying_signal and current_state == SalesState.CLOSING:
                status = ConversationStatus.COMPLETED
                if verbose:
                    print("\n[SUCCESS] Deal closed!")
                break

            if "不需要" in customer_message or "不感兴趣" in customer_message:
                if turn_number > 3:
                    status = ConversationStatus.FAILED
                    if verbose:
                        print("\n[FAILED] Customer rejected")
                    break

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

        if turn_number >= self.max_turns and status == ConversationStatus.RUNNING:
            status = ConversationStatus.MAX_TURNS_REACHED
            if verbose:
                print(f"\n[MAX TURNS] Reached {self.max_turns} turns")

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

        total_objections = sum(1 for t in turns if t.customer_objection)
        buying_signals = sum(1 for t in turns if t.customer_buying_signal)

        scores = [
            t.coach_feedback["overall_score"]
            for t in turns
            if t.coach_feedback
        ]
        average_score = sum(scores) / len(scores) if scores else 0.0

        best_turn = None
        worst_turn = None
        if scores:
            best_turn = scores.index(max(scores)) + 1
            worst_turn = scores.index(min(scores)) + 1

        strengths = []
        weaknesses = []
        recommendations = []

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

        if average_score >= 8.0:
            strengths.append(f"整体表现优秀，平均分 {average_score:.1f}/10")
        elif average_score < 6.0:
            weaknesses.append(f"整体表现需要改进，平均分 {average_score:.1f}/10")
            recommendations.append("重点学习 SPIN 和 FAB 方法论")

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
        """批量运行仿真训练"""
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
