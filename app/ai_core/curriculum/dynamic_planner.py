"""
Dynamic Curriculum Planner

Generates personalized training curriculum based on user performance.

Features:
- Weakness analysis from historical evaluations
- Personalized task generation
- Difficulty adaptation
- Progress tracking
- Learning path optimization

Usage:
    planner = DynamicCurriculumPlanner()
    curriculum = await planner.generate_curriculum(user_id=1)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class Weakness:
    """User weakness."""
    dimension: str  # methodology, objection_handling, goal_orientation, empathy, clarity
    current_score: float  # 0-10
    target_score: float  # 0-10
    gap: float  # target - current
    priority: int  # 1-5, higher is more urgent
    sample_count: int  # number of evaluations


@dataclass
class TrainingTask:
    """Personalized training task."""
    task_type: str  # conversation, drill, simulation
    focus_area: str  # opening, discovery, pitch, objection, closing
    difficulty: str  # easy, medium, hard
    target_dimension: str  # which weakness to address
    target_score: float  # expected score after completion
    estimated_duration_minutes: int
    description: str
    scenario: Dict  # task-specific scenario


@dataclass
class Curriculum:
    """Personalized curriculum."""
    user_id: int
    weaknesses: List[Weakness]
    tasks: List[TrainingTask]
    total_duration_minutes: int
    duration_days: int
    expected_improvement: Dict[str, float]  # dimension -> expected score increase
    created_at: datetime


class DynamicCurriculumPlanner:
    """
    Dynamic curriculum planner.

    Analyzes user performance and generates personalized training plans.
    """

    def __init__(self):
        self.dimension_weights = {
            "methodology": 0.25,
            "objection_handling": 0.25,
            "goal_orientation": 0.20,
            "empathy": 0.15,
            "clarity": 0.15,
        }

        self.target_scores = {
            "methodology": 8.0,
            "objection_handling": 8.5,
            "goal_orientation": 8.0,
            "empathy": 7.5,
            "clarity": 8.0,
        }

    async def generate_curriculum(
        self,
        user_id: int,
        duration_days: int = 7,
        sessions_per_day: int = 2,
    ) -> Curriculum:
        """
        Generate personalized curriculum.

        Args:
            user_id: User ID
            duration_days: Curriculum duration in days
            sessions_per_day: Training sessions per day

        Returns:
            Personalized curriculum
        """
        logger.info(f"Generating curriculum for user {user_id}")

        # 1. Analyze weaknesses
        weaknesses = await self.analyze_weaknesses(user_id)

        if not weaknesses:
            logger.warning(f"No weaknesses found for user {user_id}, using default curriculum")
            weaknesses = self._get_default_weaknesses()

        # 2. Prioritize weaknesses
        prioritized_weaknesses = self._prioritize_weaknesses(weaknesses)

        # 3. Generate tasks
        total_sessions = duration_days * sessions_per_day
        tasks = await self._generate_tasks(
            user_id,
            prioritized_weaknesses,
            total_sessions
        )

        # 4. Calculate expected improvement
        expected_improvement = self._calculate_expected_improvement(
            weaknesses,
            tasks
        )

        # 5. Create curriculum
        curriculum = Curriculum(
            user_id=user_id,
            weaknesses=prioritized_weaknesses,
            tasks=tasks,
            total_duration_minutes=sum(t.estimated_duration_minutes for t in tasks),
            duration_days=duration_days,
            expected_improvement=expected_improvement,
            created_at=datetime.now(),
        )

        logger.info(
            f"Generated curriculum with {len(tasks)} tasks "
            f"for {duration_days} days"
        )

        return curriculum

    async def analyze_weaknesses(self, user_id: int) -> List[Weakness]:
        """
        Analyze user weaknesses from historical evaluations.

        Args:
            user_id: User ID

        Returns:
            List of weaknesses
        """
        # Get user evaluations from database
        from app.models import Evaluation
        from sqlalchemy import select
        from app.database import get_session

        async with get_session() as session:
            result = await session.execute(
                select(Evaluation)
                .where(Evaluation.user_id == user_id)
                .order_by(Evaluation.created_at.desc())
                .limit(20)  # Last 20 evaluations
            )
            evaluations = result.scalars().all()

        if not evaluations:
            logger.warning(f"No evaluations found for user {user_id}")
            return []

        # Calculate average scores per dimension
        dimension_scores = {
            "methodology": [],
            "objection_handling": [],
            "goal_orientation": [],
            "empathy": [],
            "clarity": [],
        }

        for eval in evaluations:
            if eval.methodology_score:
                dimension_scores["methodology"].append(eval.methodology_score)
            if eval.objection_handling_score:
                dimension_scores["objection_handling"].append(eval.objection_handling_score)
            if eval.goal_orientation_score:
                dimension_scores["goal_orientation"].append(eval.goal_orientation_score)
            if eval.empathy_score:
                dimension_scores["empathy"].append(eval.empathy_score)
            if eval.clarity_score:
                dimension_scores["clarity"].append(eval.clarity_score)

        # Identify weaknesses
        weaknesses = []
        for dimension, scores in dimension_scores.items():
            if not scores:
                continue

            avg_score = mean(scores)
            target_score = self.target_scores[dimension]
            gap = target_score - avg_score

            # Only consider as weakness if gap > 0.5
            if gap > 0.5:
                # Calculate priority based on gap and variance
                variance = stdev(scores) if len(scores) > 1 else 0
                priority = self._calculate_priority(gap, variance)

                weaknesses.append(Weakness(
                    dimension=dimension,
                    current_score=avg_score,
                    target_score=target_score,
                    gap=gap,
                    priority=priority,
                    sample_count=len(scores),
                ))

        return weaknesses

    def _prioritize_weaknesses(self, weaknesses: List[Weakness]) -> List[Weakness]:
        """Prioritize weaknesses by priority and gap."""
        return sorted(
            weaknesses,
            key=lambda w: (w.priority, w.gap),
            reverse=True
        )

    def _calculate_priority(self, gap: float, variance: float) -> int:
        """
        Calculate weakness priority.

        Priority factors:
        - Gap size (larger gap = higher priority)
        - Variance (higher variance = higher priority, indicates inconsistency)
        """
        # Base priority from gap
        if gap >= 2.0:
            priority = 5
        elif gap >= 1.5:
            priority = 4
        elif gap >= 1.0:
            priority = 3
        elif gap >= 0.7:
            priority = 2
        else:
            priority = 1

        # Adjust for variance
        if variance > 1.5:
            priority = min(5, priority + 1)

        return priority

    async def _generate_tasks(
        self,
        user_id: int,
        weaknesses: List[Weakness],
        total_sessions: int,
    ) -> List[TrainingTask]:
        """Generate training tasks based on weaknesses."""
        tasks = []

        # Allocate sessions to weaknesses based on priority
        session_allocation = self._allocate_sessions(weaknesses, total_sessions)

        for weakness, num_sessions in session_allocation.items():
            # Generate tasks for this weakness
            weakness_tasks = self._generate_weakness_tasks(
                weakness,
                num_sessions
            )
            tasks.extend(weakness_tasks)

        return tasks

    def _allocate_sessions(
        self,
        weaknesses: List[Weakness],
        total_sessions: int,
    ) -> Dict[Weakness, int]:
        """Allocate training sessions to weaknesses."""
        if not weaknesses:
            return {}

        # Calculate weights based on priority and gap
        total_weight = sum(w.priority * w.gap for w in weaknesses)

        allocation = {}
        remaining_sessions = total_sessions

        for weakness in weaknesses[:-1]:
            weight = weakness.priority * weakness.gap
            sessions = int((weight / total_weight) * total_sessions)
            sessions = max(1, sessions)  # At least 1 session
            allocation[weakness] = sessions
            remaining_sessions -= sessions

        # Assign remaining sessions to last weakness
        if weaknesses:
            allocation[weaknesses[-1]] = max(1, remaining_sessions)

        return allocation

    def _generate_weakness_tasks(
        self,
        weakness: Weakness,
        num_sessions: int,
    ) -> List[TrainingTask]:
        """Generate tasks for a specific weakness."""
        tasks = []

        # Map dimension to focus areas and task types
        dimension_mapping = {
            "methodology": {
                "focus_areas": ["discovery", "pitch"],
                "task_types": ["conversation", "drill"],
                "scenarios": [
                    {"type": "spin_questioning", "difficulty": "medium"},
                    {"type": "fab_presentation", "difficulty": "medium"},
                ]
            },
            "objection_handling": {
                "focus_areas": ["objection"],
                "task_types": ["drill", "simulation"],
                "scenarios": [
                    {"type": "price_objection", "difficulty": "hard"},
                    {"type": "trust_objection", "difficulty": "hard"},
                    {"type": "timing_objection", "difficulty": "medium"},
                ]
            },
            "goal_orientation": {
                "focus_areas": ["opening", "closing"],
                "task_types": ["conversation", "simulation"],
                "scenarios": [
                    {"type": "rapport_building", "difficulty": "easy"},
                    {"type": "trial_close", "difficulty": "medium"},
                ]
            },
            "empathy": {
                "focus_areas": ["discovery", "objection"],
                "task_types": ["conversation", "simulation"],
                "scenarios": [
                    {"type": "active_listening", "difficulty": "medium"},
                    {"type": "emotional_response", "difficulty": "hard"},
                ]
            },
            "clarity": {
                "focus_areas": ["pitch", "closing"],
                "task_types": ["drill", "conversation"],
                "scenarios": [
                    {"type": "value_proposition", "difficulty": "medium"},
                    {"type": "next_steps", "difficulty": "easy"},
                ]
            },
        }

        mapping = dimension_mapping.get(weakness.dimension, {})
        focus_areas = mapping.get("focus_areas", ["discovery"])
        task_types = mapping.get("task_types", ["conversation"])
        scenarios = mapping.get("scenarios", [{"type": "general", "difficulty": "medium"}])

        # Generate tasks with progressive difficulty
        for i in range(num_sessions):
            # Determine difficulty progression
            if i < num_sessions * 0.3:
                difficulty = "easy"
            elif i < num_sessions * 0.7:
                difficulty = "medium"
            else:
                difficulty = "hard"

            # Select focus area and scenario
            focus_area = focus_areas[i % len(focus_areas)]
            task_type = task_types[i % len(task_types)]
            scenario = scenarios[i % len(scenarios)]

            # Calculate target score (progressive improvement)
            progress = (i + 1) / num_sessions
            target_score = weakness.current_score + (weakness.gap * progress)

            task = TrainingTask(
                task_type=task_type,
                focus_area=focus_area,
                difficulty=difficulty,
                target_dimension=weakness.dimension,
                target_score=target_score,
                estimated_duration_minutes=20,
                description=self._generate_task_description(
                    weakness.dimension,
                    focus_area,
                    scenario["type"],
                    difficulty
                ),
                scenario={
                    "type": scenario["type"],
                    "difficulty": difficulty,
                    "focus_dimension": weakness.dimension,
                }
            )

            tasks.append(task)

        return tasks

    def _generate_task_description(
        self,
        dimension: str,
        focus_area: str,
        scenario_type: str,
        difficulty: str,
    ) -> str:
        """Generate task description."""
        descriptions = {
            "methodology": {
                "spin_questioning": "使用SPIN提问法挖掘客户需求",
                "fab_presentation": "使用FAB法则呈现产品价值",
            },
            "objection_handling": {
                "price_objection": "处理客户的价格异议",
                "trust_objection": "建立客户信任，消除疑虑",
                "timing_objection": "处理客户的时机异议",
            },
            "goal_orientation": {
                "rapport_building": "快速建立客户信任关系",
                "trial_close": "尝试性成交，推进销售进程",
            },
            "empathy": {
                "active_listening": "积极倾听，理解客户真实需求",
                "emotional_response": "同理心回应客户情绪",
            },
            "clarity": {
                "value_proposition": "清晰表达产品价值主张",
                "next_steps": "明确说明下一步行动",
            },
        }

        base_desc = descriptions.get(dimension, {}).get(
            scenario_type,
            f"{focus_area}阶段训练"
        )

        difficulty_suffix = {
            "easy": "（基础练习）",
            "medium": "（进阶练习）",
            "hard": "（高难度挑战）",
        }

        return f"{base_desc}{difficulty_suffix.get(difficulty, '')}"

    def _calculate_expected_improvement(
        self,
        weaknesses: List[Weakness],
        tasks: List[TrainingTask],
    ) -> Dict[str, float]:
        """Calculate expected improvement per dimension."""
        improvement = {}

        # Group tasks by dimension
        dimension_tasks = {}
        for task in tasks:
            dim = task.target_dimension
            if dim not in dimension_tasks:
                dimension_tasks[dim] = []
            dimension_tasks[dim].append(task)

        # Calculate expected improvement
        for weakness in weaknesses:
            dim = weakness.dimension
            if dim in dimension_tasks:
                # Average improvement from tasks
                target_scores = [t.target_score for t in dimension_tasks[dim]]
                expected_final_score = max(target_scores)
                improvement[dim] = expected_final_score - weakness.current_score
            else:
                improvement[dim] = 0.0

        return improvement

    def _get_default_weaknesses(self) -> List[Weakness]:
        """Get default weaknesses for new users."""
        return [
            Weakness(
                dimension="methodology",
                current_score=6.0,
                target_score=8.0,
                gap=2.0,
                priority=3,
                sample_count=0,
            ),
            Weakness(
                dimension="objection_handling",
                current_score=5.5,
                target_score=8.5,
                gap=3.0,
                priority=4,
                sample_count=0,
            ),
        ]
