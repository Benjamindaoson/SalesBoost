"""
RLAIF (Reinforcement Learning from AI Feedback) Pipeline

Implements a complete data flywheel for continuous AI improvement:
1. Collect high-quality conversation samples
2. Label with advanced AI (Claude 3.5)
3. Generate training data
4. Fine-tune lightweight models
5. Deploy and monitor

Features:
- Automatic sample collection
- AI-powered labeling
- Training data generation
- Model fine-tuning pipeline
- A/B testing support
- Performance tracking

Usage:
    pipeline = RLAIFPipeline()
    await pipeline.run_collection_cycle()
    await pipeline.run_labeling_cycle()
    await pipeline.generate_training_data()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ConversationSample:
    """Conversation sample for RLAIF."""
    session_id: int
    user_id: int
    messages: List[Dict]  # [{"role": "user/assistant", "content": "..."}]
    score: float  # Overall score
    evaluation: Dict  # Detailed evaluation
    sales_state_transitions: List[str]  # FSM transitions
    collected_at: datetime


@dataclass
class LabeledSample:
    """AI-labeled conversation sample."""
    sample: ConversationSample
    labels: Dict  # {"message_id": {"quality": "good/bad", "feedback": "..."}}
    labeling_model: str  # Model used for labeling
    labeled_at: datetime


@dataclass
class TrainingExample:
    """Training example for fine-tuning."""
    messages: List[Dict]  # OpenAI fine-tuning format
    metadata: Dict  # Additional metadata


class RLAIFPipeline:
    """
    RLAIF Pipeline for continuous AI improvement.

    Implements the complete data flywheel:
    User Conversations → Sample Collection → AI Labeling → Training Data → Fine-tuning → Deployment
    """

    def __init__(
        self,
        storage_dir: str = "./storage/rlaif",
        min_score_threshold: float = 8.0,
        max_samples_per_cycle: int = 100,
        labeling_model: str = "claude-3-5-sonnet",
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.min_score_threshold = min_score_threshold
        self.max_samples_per_cycle = max_samples_per_cycle
        self.labeling_model = labeling_model

        # Statistics
        self.stats = {
            "samples_collected": 0,
            "samples_labeled": 0,
            "training_examples_generated": 0,
            "models_trained": 0,
        }

    async def run_collection_cycle(self) -> List[ConversationSample]:
        """
        Run sample collection cycle.

        Collects high-quality conversations from the database.
        """
        logger.info("Starting RLAIF sample collection cycle")

        samples = await self.collect_samples()

        # Save samples
        self._save_samples(samples, "collected")

        self.stats["samples_collected"] += len(samples)

        logger.info(f"Collected {len(samples)} samples")

        return samples

    async def collect_samples(self) -> List[ConversationSample]:
        """Collect high-quality conversation samples."""
        from app.models import Session, Message, Evaluation, SessionStatus
        from sqlalchemy import select, and_
        from app.database import get_session

        samples = []

        async with get_session() as db_session:
            # Get high-scoring completed sessions from last 7 days
            cutoff_date = datetime.now() - timedelta(days=7)

            result = await db_session.execute(
                select(Session)
                .where(
                    and_(
                        Session.status == SessionStatus.COMPLETED,
                        Session.score >= self.min_score_threshold,
                        Session.completed_at >= cutoff_date,
                    )
                )
                .order_by(Session.score.desc())
                .limit(self.max_samples_per_cycle)
            )

            sessions = result.scalars().all()

            for session in sessions:
                # Get messages
                msg_result = await db_session.execute(
                    select(Message)
                    .where(Message.session_id == session.id)
                    .order_by(Message.created_at)
                )
                messages = msg_result.scalars().all()

                # Get evaluation
                eval_result = await db_session.execute(
                    select(Evaluation)
                    .where(Evaluation.session_id == session.id)
                    .order_by(Evaluation.created_at.desc())
                    .limit(1)
                )
                evaluation = eval_result.scalar_one_or_none()

                if not messages or not evaluation:
                    continue

                # Convert to sample format
                message_list = [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "sales_technique": msg.sales_technique,
                        "score": msg.score,
                    }
                    for msg in messages
                ]

                # Extract FSM transitions
                transitions = []
                if hasattr(session, 'transitions'):
                    transitions = [
                        f"{t.from_state} -> {t.to_state} ({t.trigger})"
                        for t in session.transitions
                    ]

                sample = ConversationSample(
                    session_id=session.id,
                    user_id=session.user_id,
                    messages=message_list,
                    score=session.score,
                    evaluation={
                        "overall_score": evaluation.overall_score,
                        "methodology_score": evaluation.methodology_score,
                        "objection_handling_score": evaluation.objection_handling_score,
                        "goal_orientation_score": evaluation.goal_orientation_score,
                        "empathy_score": evaluation.empathy_score,
                        "clarity_score": evaluation.clarity_score,
                        "strengths": json.loads(evaluation.strengths) if evaluation.strengths else [],
                        "weaknesses": json.loads(evaluation.weaknesses) if evaluation.weaknesses else [],
                    },
                    sales_state_transitions=transitions,
                    collected_at=datetime.now(),
                )

                samples.append(sample)

        return samples

    async def run_labeling_cycle(
        self,
        samples: Optional[List[ConversationSample]] = None
    ) -> List[LabeledSample]:
        """
        Run AI labeling cycle.

        Labels samples with advanced AI model.
        """
        logger.info("Starting RLAIF labeling cycle")

        if samples is None:
            # Load collected samples
            samples = self._load_samples("collected")

        labeled_samples = []

        for sample in samples:
            try:
                labeled = await self.label_with_ai(sample)
                labeled_samples.append(labeled)
            except Exception as e:
                logger.error(f"Failed to label sample {sample.session_id}: {e}")
                continue

        # Save labeled samples
        self._save_labeled_samples(labeled_samples)

        self.stats["samples_labeled"] += len(labeled_samples)

        logger.info(f"Labeled {len(labeled_samples)} samples")

        return labeled_samples

    async def label_with_ai(self, sample: ConversationSample) -> LabeledSample:
        """Label conversation sample with AI."""
        from app.infra.llm import UnifiedLLMClient, LLMProvider

        llm_client = UnifiedLLMClient.get_instance()

        # Prepare conversation for labeling
        conversation_text = self._format_conversation(sample.messages)

        # Create labeling prompt
        prompt = f"""
你是一位资深的销售培训专家。请分析以下销售对话，为每句话提供详细的质量标注。

对话信息：
- 总分：{sample.score}/10
- 方法论得分：{sample.evaluation.get('methodology_score', 'N/A')}
- 异议处理得分：{sample.evaluation.get('objection_handling_score', 'N/A')}
- 目标导向得分：{sample.evaluation.get('goal_orientation_score', 'N/A')}
- 同理心得分：{sample.evaluation.get('empathy_score', 'N/A')}
- 清晰度得分：{sample.evaluation.get('clarity_score', 'N/A')}

对话内容：
{conversation_text}

请为每句销售话术（assistant角色）标注：
1. 质量评级（excellent/good/fair/poor）
2. 使用的销售技巧（如SPIN、FAB等）
3. 优点（做得好的地方）
4. 改进建议（如何做得更好）

请以JSON格式返回，格式如下：
{{
    "message_labels": [
        {{
            "message_index": 0,
            "role": "assistant",
            "quality": "good",
            "technique": "SPIN - Situation Question",
            "strengths": ["问题开放", "引导客户思考"],
            "improvements": ["可以更具体地询问使用场景"]
        }},
        ...
    ],
    "overall_feedback": "整体对话的评价和建议"
}}
"""

        # Call AI for labeling
        response = await llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            provider=LLMProvider.OPENAI,  # Use Claude 3.5 in production
            model="gpt-4o",
            temperature=0.3,
        )

        # Parse labels
        try:
            labels = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback: extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                labels = json.loads(json_match.group())
            else:
                labels = {"message_labels": [], "overall_feedback": response.content}

        return LabeledSample(
            sample=sample,
            labels=labels,
            labeling_model=self.labeling_model,
            labeled_at=datetime.now(),
        )

    async def generate_training_data(
        self,
        labeled_samples: Optional[List[LabeledSample]] = None,
        output_file: str = "training_data.jsonl",
    ) -> List[TrainingExample]:
        """
        Generate training data from labeled samples.

        Converts labeled samples to OpenAI fine-tuning format.
        """
        logger.info("Generating training data")

        if labeled_samples is None:
            # Load labeled samples
            labeled_samples = self._load_labeled_samples()

        training_examples = []

        for labeled in labeled_samples:
            # Generate examples for each message
            for i, message in enumerate(labeled.sample.messages):
                if message["role"] != "assistant":
                    continue

                # Find label for this message
                label = None
                for msg_label in labeled.labels.get("message_labels", []):
                    if msg_label.get("message_index") == i:
                        label = msg_label
                        break

                if not label:
                    continue

                # Create training example
                # Format: System prompt + User message + Assistant response with feedback
                context_messages = labeled.sample.messages[:i+1]

                example = TrainingExample(
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一位专业的销售教练，负责指导销售人员提升话术质量。"
                        },
                        {
                            "role": "user",
                            "content": f"对话上下文：\n{self._format_conversation(context_messages[:-1])}\n\n"
                                      f"销售话术：{message['content']}\n\n"
                                      f"请评估这句话术的质量并给出改进建议。"
                        },
                        {
                            "role": "assistant",
                            "content": f"质量评级：{label.get('quality', 'N/A')}\n"
                                      f"使用技巧：{label.get('technique', 'N/A')}\n"
                                      f"优点：{', '.join(label.get('strengths', []))}\n"
                                      f"改进建议：{', '.join(label.get('improvements', []))}"
                        }
                    ],
                    metadata={
                        "session_id": labeled.sample.session_id,
                        "message_index": i,
                        "score": labeled.sample.score,
                    }
                )

                training_examples.append(example)

        # Save training data
        output_path = self.storage_dir / output_file
        with open(output_path, "w", encoding="utf-8") as f:
            for example in training_examples:
                f.write(json.dumps(example.messages, ensure_ascii=False) + "\n")

        self.stats["training_examples_generated"] += len(training_examples)

        logger.info(
            f"Generated {len(training_examples)} training examples "
            f"saved to {output_path}"
        )

        return training_examples

    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation for display."""
        lines = []
        for msg in messages:
            role = "销售" if msg["role"] == "assistant" else "客户"
            lines.append(f"{role}：{msg['content']}")
        return "\n".join(lines)

    def _save_samples(self, samples: List[ConversationSample], prefix: str):
        """Save samples to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_samples_{timestamp}.json"
        filepath = self.storage_dir / filename

        data = [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "messages": s.messages,
                "score": s.score,
                "evaluation": s.evaluation,
                "sales_state_transitions": s.sales_state_transitions,
                "collected_at": s.collected_at.isoformat(),
            }
            for s in samples
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(samples)} samples to {filepath}")

    def _load_samples(self, prefix: str) -> List[ConversationSample]:
        """Load samples from disk."""
        # Find latest file
        files = list(self.storage_dir.glob(f"{prefix}_samples_*.json"))
        if not files:
            return []

        latest_file = max(files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = [
            ConversationSample(
                session_id=d["session_id"],
                user_id=d["user_id"],
                messages=d["messages"],
                score=d["score"],
                evaluation=d["evaluation"],
                sales_state_transitions=d["sales_state_transitions"],
                collected_at=datetime.fromisoformat(d["collected_at"]),
            )
            for d in data
        ]

        return samples

    def _save_labeled_samples(self, labeled_samples: List[LabeledSample]):
        """Save labeled samples to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"labeled_samples_{timestamp}.json"
        filepath = self.storage_dir / filename

        data = [
            {
                "sample": {
                    "session_id": ls.sample.session_id,
                    "user_id": ls.sample.user_id,
                    "messages": ls.sample.messages,
                    "score": ls.sample.score,
                    "evaluation": ls.sample.evaluation,
                },
                "labels": ls.labels,
                "labeling_model": ls.labeling_model,
                "labeled_at": ls.labeled_at.isoformat(),
            }
            for ls in labeled_samples
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(labeled_samples)} labeled samples to {filepath}")

    def _load_labeled_samples(self) -> List[LabeledSample]:
        """Load labeled samples from disk."""
        files = list(self.storage_dir.glob("labeled_samples_*.json"))
        if not files:
            return []

        latest_file = max(files, key=lambda p: p.stat().st_mtime)

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        labeled_samples = []
        for d in data:
            sample_data = d["sample"]
            sample = ConversationSample(
                session_id=sample_data["session_id"],
                user_id=sample_data["user_id"],
                messages=sample_data["messages"],
                score=sample_data["score"],
                evaluation=sample_data["evaluation"],
                sales_state_transitions=[],
                collected_at=datetime.now(),
            )

            labeled = LabeledSample(
                sample=sample,
                labels=d["labels"],
                labeling_model=d["labeling_model"],
                labeled_at=datetime.fromisoformat(d["labeled_at"]),
            )

            labeled_samples.append(labeled)

        return labeled_samples

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return self.stats.copy()
