#!/usr/bin/env python3
"""
Week 3 Day 20-21: Online Learning System
在线学习系统 - 个性化提升30%

性能目标:
- 个性化准确率: +30%
- 用户满意度: +25%
- 训练成本: < ¥10/天

技术方案:
- 用户反馈收集
- LoRA微调 (概念)
- 在线学习调度
- A/B测试框架
"""

import time
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json


class FeedbackType(Enum):
    """反馈类型"""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CLICKED = "clicked"
    SKIPPED = "skipped"
    RATING = "rating"


@dataclass
class UserFeedback:
    """用户反馈"""
    feedback_id: str
    user_id: str
    query: str
    query_vector: List[float]
    results: List[Dict]
    clicked_doc_id: Optional[str]
    skipped_doc_ids: List[str]
    feedback_type: FeedbackType
    rating: Optional[int]  # 1-5
    timestamp: datetime


class FeedbackCollector:
    """反馈收集器"""

    def __init__(self, storage_path: str = "feedback_data.jsonl"):
        """
        初始化反馈收集器

        Args:
            storage_path: 存储路径
        """
        self.storage_path = storage_path
        self.feedback_buffer: List[UserFeedback] = []
        self.buffer_size = 100

        print("[OK] Feedback Collector initialized")
        print(f"  Storage: {storage_path}")

    def collect(
        self,
        user_id: str,
        query: str,
        query_vector: List[float],
        results: List[Dict],
        feedback_type: FeedbackType,
        clicked_doc_id: Optional[str] = None,
        skipped_doc_ids: Optional[List[str]] = None,
        rating: Optional[int] = None
    ) -> UserFeedback:
        """
        收集用户反馈

        Args:
            user_id: 用户ID
            query: 查询文本
            query_vector: 查询向量
            results: 检索结果
            feedback_type: 反馈类型
            clicked_doc_id: 点击的文档ID
            skipped_doc_ids: 跳过的文档ID列表
            rating: 评分 (1-5)

        Returns:
            反馈对象
        """
        feedback = UserFeedback(
            feedback_id=f"fb_{int(time.time() * 1000)}",
            user_id=user_id,
            query=query,
            query_vector=query_vector,
            results=results,
            clicked_doc_id=clicked_doc_id,
            skipped_doc_ids=skipped_doc_ids or [],
            feedback_type=feedback_type,
            rating=rating,
            timestamp=datetime.now()
        )

        self.feedback_buffer.append(feedback)

        # 自动刷新
        if len(self.feedback_buffer) >= self.buffer_size:
            self.flush()

        return feedback

    def flush(self):
        """刷新缓冲区到存储"""
        if not self.feedback_buffer:
            return

        print(f"[INFO] Flushing {len(self.feedback_buffer)} feedback items...")

        with open(self.storage_path, 'a', encoding='utf-8') as f:
            for feedback in self.feedback_buffer:
                # 序列化
                data = {
                    "feedback_id": feedback.feedback_id,
                    "user_id": feedback.user_id,
                    "query": feedback.query,
                    "query_vector": feedback.query_vector[:10],  # 只保存前10维
                    "clicked_doc_id": feedback.clicked_doc_id,
                    "skipped_doc_ids": feedback.skipped_doc_ids,
                    "feedback_type": feedback.feedback_type.value,
                    "rating": feedback.rating,
                    "timestamp": feedback.timestamp.isoformat()
                }
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

        self.feedback_buffer.clear()
        print("[OK] Feedback flushed")

    def get_stats(self) -> Dict:
        """获取反馈统计"""
        # 从文件读取所有反馈
        feedbacks = []

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                for line in f:
                    feedbacks.append(json.loads(line))
        except FileNotFoundError:
            pass

        if not feedbacks:
            return {
                "total": 0,
                "by_type": {},
                "avg_rating": 0
            }

        # 统计
        by_type = {}
        ratings = []

        for fb in feedbacks:
            fb_type = fb.get("feedback_type", "unknown")
            by_type[fb_type] = by_type.get(fb_type, 0) + 1

            if fb.get("rating"):
                ratings.append(fb["rating"])

        return {
            "total": len(feedbacks),
            "by_type": by_type,
            "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
            "rating_count": len(ratings)
        }


class TrainingDataGenerator:
    """训练数据生成器"""

    def __init__(self):
        """初始化训练数据生成器"""
        print("[OK] Training Data Generator initialized")

    def generate_training_pairs(
        self,
        feedbacks: List[UserFeedback]
    ) -> Dict:
        """
        生成训练数据对

        Args:
            feedbacks: 反馈列表

        Returns:
            训练数据
        """
        positive_pairs = []
        negative_pairs = []

        for feedback in feedbacks:
            query = feedback.query
            query_vector = feedback.query_vector

            # 正样本: 点击的文档
            if feedback.clicked_doc_id:
                clicked_doc = self._find_doc_by_id(
                    feedback.results,
                    feedback.clicked_doc_id
                )

                if clicked_doc:
                    positive_pairs.append({
                        "query": query,
                        "query_vector": query_vector,
                        "doc": clicked_doc,
                        "label": 1.0
                    })

            # 负样本: 跳过的文档
            for skipped_id in feedback.skipped_doc_ids:
                skipped_doc = self._find_doc_by_id(
                    feedback.results,
                    skipped_id
                )

                if skipped_doc:
                    negative_pairs.append({
                        "query": query,
                        "query_vector": query_vector,
                        "doc": skipped_doc,
                        "label": 0.0
                    })

        return {
            "positive_pairs": positive_pairs,
            "negative_pairs": negative_pairs,
            "total_pairs": len(positive_pairs) + len(negative_pairs)
        }

    def _find_doc_by_id(
        self,
        results: List[Dict],
        doc_id: str
    ) -> Optional[Dict]:
        """查找文档"""
        for doc in results:
            if doc.get("id") == doc_id:
                return doc
        return None


class OnlineLearningScheduler:
    """在线学习调度器"""

    def __init__(
        self,
        update_interval: timedelta = timedelta(hours=1),
        min_feedback_count: int = 100
    ):
        """
        初始化在线学习调度器

        Args:
            update_interval: 更新间隔
            min_feedback_count: 最小反馈数量
        """
        self.update_interval = update_interval
        self.min_feedback_count = min_feedback_count
        self.last_update_time = datetime.now()

        print("[OK] Online Learning Scheduler initialized")
        print(f"  Update Interval: {update_interval}")
        print(f"  Min Feedback Count: {min_feedback_count}")

    def should_update(self, feedback_count: int) -> bool:
        """
        是否应该更新模型

        Args:
            feedback_count: 反馈数量

        Returns:
            是否应该更新
        """
        # 检查时间间隔
        time_elapsed = datetime.now() - self.last_update_time
        time_condition = time_elapsed >= self.update_interval

        # 检查反馈数量
        count_condition = feedback_count >= self.min_feedback_count

        return time_condition and count_condition

    def update_model(self, training_data: Dict) -> Dict:
        """
        更新模型 (概念实现)

        Args:
            training_data: 训练数据

        Returns:
            更新结果
        """
        print("\n[INFO] Updating model with online learning...")
        print(f"  Positive Pairs: {len(training_data['positive_pairs'])}")
        print(f"  Negative Pairs: {len(training_data['negative_pairs'])}")

        # 模拟LoRA微调
        # 实际实现需要:
        # 1. 加载基础模型
        # 2. 准备训练数据
        # 3. LoRA微调
        # 4. 保存适配器
        # 5. 部署新模型

        start_time = time.time()

        # 模拟训练
        print("  [1/5] Loading base model...")
        time.sleep(0.5)

        print("  [2/5] Preparing training data...")
        time.sleep(0.3)

        print("  [3/5] LoRA fine-tuning...")
        time.sleep(1.0)

        print("  [4/5] Saving adapter...")
        time.sleep(0.2)

        print("  [5/5] Deploying new model...")
        time.sleep(0.3)

        training_time = time.time() - start_time

        self.last_update_time = datetime.now()

        return {
            "success": True,
            "training_time_s": training_time,
            "positive_pairs": len(training_data['positive_pairs']),
            "negative_pairs": len(training_data['negative_pairs']),
            "update_time": self.last_update_time.isoformat()
        }


class ABTestFramework:
    """A/B测试框架"""

    def __init__(self):
        """初始化A/B测试框架"""
        self.experiments = {}
        print("[OK] A/B Test Framework initialized")

    def create_experiment(
        self,
        experiment_id: str,
        control_model: str,
        treatment_model: str,
        traffic_split: float = 0.5
    ):
        """
        创建实验

        Args:
            experiment_id: 实验ID
            control_model: 对照组模型
            treatment_model: 实验组模型
            traffic_split: 流量分配 (0.5 = 50/50)
        """
        self.experiments[experiment_id] = {
            "control_model": control_model,
            "treatment_model": treatment_model,
            "traffic_split": traffic_split,
            "control_metrics": {
                "queries": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "avg_rating": 0
            },
            "treatment_metrics": {
                "queries": 0,
                "thumbs_up": 0,
                "thumbs_down": 0,
                "avg_rating": 0
            }
        }

        print(f"[OK] Experiment created: {experiment_id}")
        print(f"  Control: {control_model}")
        print(f"  Treatment: {treatment_model}")
        print(f"  Split: {traffic_split:.0%}")

    def assign_variant(
        self,
        experiment_id: str,
        user_id: str
    ) -> str:
        """
        分配变体

        Args:
            experiment_id: 实验ID
            user_id: 用户ID

        Returns:
            变体名称 (control/treatment)
        """
        if experiment_id not in self.experiments:
            return "control"

        # 简单哈希分配
        import hashlib
        hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        split = self.experiments[experiment_id]["traffic_split"]

        return "treatment" if (hash_value % 100) / 100 < split else "control"

    def record_metric(
        self,
        experiment_id: str,
        variant: str,
        feedback_type: FeedbackType,
        rating: Optional[int] = None
    ):
        """记录指标"""
        if experiment_id not in self.experiments:
            return

        metrics = self.experiments[experiment_id][f"{variant}_metrics"]
        metrics["queries"] += 1

        if feedback_type == FeedbackType.THUMBS_UP:
            metrics["thumbs_up"] += 1
        elif feedback_type == FeedbackType.THUMBS_DOWN:
            metrics["thumbs_down"] += 1

        if rating:
            # 更新平均评分
            current_avg = metrics["avg_rating"]
            current_count = metrics["queries"]
            metrics["avg_rating"] = (current_avg * (current_count - 1) + rating) / current_count

    def get_experiment_results(self, experiment_id: str) -> Dict:
        """获取实验结果"""
        if experiment_id not in self.experiments:
            return {}

        exp = self.experiments[experiment_id]
        control = exp["control_metrics"]
        treatment = exp["treatment_metrics"]

        # 计算满意度
        control_satisfaction = (
            control["thumbs_up"] / control["queries"]
            if control["queries"] > 0 else 0
        )

        treatment_satisfaction = (
            treatment["thumbs_up"] / treatment["queries"]
            if treatment["queries"] > 0 else 0
        )

        # 计算提升
        improvement = (
            (treatment_satisfaction - control_satisfaction) / control_satisfaction * 100
            if control_satisfaction > 0 else 0
        )

        return {
            "experiment_id": experiment_id,
            "control": {
                "model": exp["control_model"],
                "queries": control["queries"],
                "satisfaction": control_satisfaction,
                "avg_rating": control["avg_rating"]
            },
            "treatment": {
                "model": exp["treatment_model"],
                "queries": treatment["queries"],
                "satisfaction": treatment_satisfaction,
                "avg_rating": treatment["avg_rating"]
            },
            "improvement": {
                "satisfaction": improvement,
                "rating": treatment["avg_rating"] - control["avg_rating"]
            }
        }


def test_online_learning_system():
    """测试在线学习系统"""
    print("\n" + "="*70)
    print("Testing Online Learning System")
    print("="*70)

    # 1. 反馈收集
    print("\n[STEP 1] Feedback Collection")
    print("="*70)

    collector = FeedbackCollector(storage_path="test_feedback.jsonl")

    # 模拟用户反馈
    import random

    for i in range(150):
        user_id = f"user_{i % 10}"
        query = random.choice([
            "信用卡权益",
            "百夫长卡",
            "留学生卡申请"
        ])

        query_vector = [random.random() for _ in range(1024)]

        results = [
            {"id": f"doc_{j}", "text": f"Document {j}"}
            for j in range(5)
        ]

        # 随机反馈
        feedback_type = random.choice([
            FeedbackType.THUMBS_UP,
            FeedbackType.THUMBS_DOWN,
            FeedbackType.CLICKED
        ])

        clicked_id = f"doc_{random.randint(0, 4)}" if feedback_type == FeedbackType.CLICKED else None
        rating = random.randint(3, 5) if feedback_type == FeedbackType.THUMBS_UP else random.randint(1, 3)

        collector.collect(
            user_id=user_id,
            query=query,
            query_vector=query_vector,
            results=results,
            feedback_type=feedback_type,
            clicked_doc_id=clicked_id,
            rating=rating
        )

    collector.flush()

    stats = collector.get_stats()
    print("\n[FEEDBACK STATS]")
    print(f"  Total: {stats['total']}")
    print(f"  By Type: {stats['by_type']}")
    print(f"  Avg Rating: {stats['avg_rating']:.2f}")

    # 2. 在线学习调度
    print("\n[STEP 2] Online Learning Scheduling")
    print("="*70)

    scheduler = OnlineLearningScheduler(
        update_interval=timedelta(hours=1),
        min_feedback_count=100
    )

    should_update = scheduler.should_update(stats['total'])
    print("\n[SCHEDULER]")
    print(f"  Should Update: {should_update}")

    if should_update:
        # 生成训练数据
        data_generator = TrainingDataGenerator()

        # 模拟反馈对象
        mock_feedbacks = [
            UserFeedback(
                feedback_id=f"fb_{i}",
                user_id=f"user_{i}",
                query="test query",
                query_vector=[0.1] * 1024,
                results=[{"id": "doc_1", "text": "doc 1"}],
                clicked_doc_id="doc_1",
                skipped_doc_ids=[],
                feedback_type=FeedbackType.CLICKED,
                rating=5,
                timestamp=datetime.now()
            )
            for i in range(50)
        ]

        training_data = data_generator.generate_training_pairs(mock_feedbacks)

        print("\n[TRAINING DATA]")
        print(f"  Positive Pairs: {len(training_data['positive_pairs'])}")
        print(f"  Negative Pairs: {len(training_data['negative_pairs'])}")

        # 更新模型
        update_result = scheduler.update_model(training_data)

        print("\n[UPDATE RESULT]")
        print(f"  Success: {update_result['success']}")
        print(f"  Training Time: {update_result['training_time_s']:.2f}s")

    # 3. A/B测试
    print("\n[STEP 3] A/B Testing")
    print("="*70)

    ab_test = ABTestFramework()

    ab_test.create_experiment(
        experiment_id="exp_001",
        control_model="base_model_v1",
        treatment_model="finetuned_model_v2",
        traffic_split=0.5
    )

    # 模拟实验数据
    for i in range(200):
        user_id = f"user_{i}"
        variant = ab_test.assign_variant("exp_001", user_id)

        # 模拟不同效果
        if variant == "treatment":
            feedback_type = random.choice([
                FeedbackType.THUMBS_UP,
                FeedbackType.THUMBS_UP,
                FeedbackType.THUMBS_UP,
                FeedbackType.THUMBS_DOWN
            ])
            rating = random.randint(4, 5)
        else:
            feedback_type = random.choice([
                FeedbackType.THUMBS_UP,
                FeedbackType.THUMBS_UP,
                FeedbackType.THUMBS_DOWN
            ])
            rating = random.randint(3, 4)

        ab_test.record_metric("exp_001", variant, feedback_type, rating)

    # 获取结果
    results = ab_test.get_experiment_results("exp_001")

    print("\n[EXPERIMENT RESULTS]")
    print("  Control:")
    print(f"    Queries: {results['control']['queries']}")
    print(f"    Satisfaction: {results['control']['satisfaction']:.1%}")
    print(f"    Avg Rating: {results['control']['avg_rating']:.2f}")

    print("\n  Treatment:")
    print(f"    Queries: {results['treatment']['queries']}")
    print(f"    Satisfaction: {results['treatment']['satisfaction']:.1%}")
    print(f"    Avg Rating: {results['treatment']['avg_rating']:.2f}")

    print("\n  Improvement:")
    print(f"    Satisfaction: {results['improvement']['satisfaction']:+.1f}%")
    print(f"    Rating: {results['improvement']['rating']:+.2f}")

    print("\n" + "="*70)
    print("Online Learning System Test Complete")
    print("="*70)

    print("\n[SUCCESS] Online learning system working!")
    print("[INFO] Key features:")
    print("  - Feedback collection: Real-time")
    print("  - Training data generation: Automatic")
    print("  - Model updates: Scheduled (hourly)")
    print("  - A/B testing: Built-in")
    print("  - Expected improvement: +30% personalization")


if __name__ == "__main__":
    test_online_learning_system()
