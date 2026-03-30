"""
Phase 3B Week 6 Day 3-4: Sales Coach Agent

核心目标：构建"上帝视角"的金牌教练，实时分析 Sales Agent 的表现并提供改进建议。

评估维度：
1. 方法论执行度 (Methodology Adherence): 是否使用 SPIN/FAB
2. 异议处理质量 (Objection Handling): 是否有效处理异议
3. 目标推进力 (Goal Orientation): 是否推进 FSM 状态
4. 对话评分 (Scoring): 0-10 分 + 具体建议

这是 RLAIF (Reinforcement Learning from AI Feedback) 的雏形！

实现日期: 2026-02-02
"""

import logging
import sys
import os
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState

logger = logging.getLogger(__name__)


class EvaluationDimension(str, Enum):
    """评估维度"""
    METHODOLOGY = "methodology"              # 方法论执行
    OBJECTION_HANDLING = "objection_handling"  # 异议处理
    GOAL_ORIENTATION = "goal_orientation"    # 目标推进
    EMPATHY = "empathy"                      # 同理心
    CLARITY = "clarity"                      # 表达清晰度


@dataclass
class EvaluationCriteria:
    """评估标准"""
    dimension: EvaluationDimension
    weight: float  # 权重 (0-1)
    description: str
    pass_threshold: float  # 及格线 (0-10)


@dataclass
class CoachFeedback:
    """教练反馈"""
    overall_score: float  # 总分 (0-10)
    dimension_scores: Dict[str, float]  # 各维度得分
    stage_alignment: str  # Pass/Fail
    technique_used: str  # 使用的技巧
    critique: str  # 批评
    suggestion: str  # 建议
    strengths: List[str]  # 优点
    weaknesses: List[str]  # 缺点


class EvaluationRubric:
    """
    评估标准库

    为不同的 FSM 阶段定义评分标准
    """

    def __init__(self):
        self.criteria_by_stage: Dict[SalesState, List[EvaluationCriteria]] = {}
        self._initialize_rubrics()

    def _initialize_rubrics(self):
        """初始化评估标准"""

        # Opening 阶段标准
        self.criteria_by_stage[SalesState.OPENING] = [
            EvaluationCriteria(
                dimension=EvaluationDimension.METHODOLOGY,
                weight=0.3,
                description="是否进行了简短自我介绍和破冰",
                pass_threshold=6.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.EMPATHY,
                weight=0.3,
                description="是否表现出友好和尊重",
                pass_threshold=6.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.GOAL_ORIENTATION,
                weight=0.2,
                description="是否尝试引导进入 Discovery",
                pass_threshold=5.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.CLARITY,
                weight=0.2,
                description="表达是否清晰简洁",
                pass_threshold=6.0
            )
        ]

        # Discovery 阶段标准
        self.criteria_by_stage[SalesState.DISCOVERY] = [
            EvaluationCriteria(
                dimension=EvaluationDimension.METHODOLOGY,
                weight=0.4,
                description="是否使用 SPIN 提问法",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.EMPATHY,
                weight=0.2,
                description="是否认真倾听客户回答",
                pass_threshold=6.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.GOAL_ORIENTATION,
                weight=0.3,
                description="是否收集到有效信息",
                pass_threshold=6.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.CLARITY,
                weight=0.1,
                description="问题是否清晰",
                pass_threshold=7.0
            )
        ]

        # Pitch 阶段标准
        self.criteria_by_stage[SalesState.PITCH] = [
            EvaluationCriteria(
                dimension=EvaluationDimension.METHODOLOGY,
                weight=0.5,
                description="是否使用 FAB 法则呈现",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.GOAL_ORIENTATION,
                weight=0.3,
                description="是否针对客户需求推介",
                pass_threshold=6.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.CLARITY,
                weight=0.2,
                description="是否清晰表达价值",
                pass_threshold=7.0
            )
        ]

        # Objection 阶段标准
        self.criteria_by_stage[SalesState.OBJECTION] = [
            EvaluationCriteria(
                dimension=EvaluationDimension.OBJECTION_HANDLING,
                weight=0.5,
                description="是否有效处理异议",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.EMPATHY,
                weight=0.3,
                description="是否表现出同理心",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.GOAL_ORIENTATION,
                weight=0.2,
                description="是否尝试解决并推进",
                pass_threshold=6.0
            )
        ]

        # Closing 阶段标准
        self.criteria_by_stage[SalesState.CLOSING] = [
            EvaluationCriteria(
                dimension=EvaluationDimension.METHODOLOGY,
                weight=0.4,
                description="是否使用成交技巧",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.GOAL_ORIENTATION,
                weight=0.4,
                description="是否明确推进下一步",
                pass_threshold=7.0
            ),
            EvaluationCriteria(
                dimension=EvaluationDimension.CLARITY,
                weight=0.2,
                description="是否清晰说明流程",
                pass_threshold=6.0
            )
        ]

        logger.info(f"Initialized evaluation rubrics for {len(self.criteria_by_stage)} stages")

    def get_criteria(self, stage: SalesState) -> List[EvaluationCriteria]:
        """获取指定阶段的评估标准"""
        return self.criteria_by_stage.get(stage, [])


class SalesCoach:
    """
    销售教练 Agent

    核心功能：
    1. 实时分析 Sales Agent 的表现
    2. 评估方法论执行情况
    3. 提供具体的改进建议
    4. 生成复盘报告
    """

    def __init__(self):
        self.rubric = EvaluationRubric()
        logger.info("SalesCoach initialized")

    def evaluate_response(
        self,
        sales_message: str,
        customer_message: str,
        current_stage: SalesState,
        conversation_history: List[Dict[str, str]] = None
    ) -> CoachFeedback:
        """
        评估 Sales Agent 的响应

        Args:
            sales_message: Sales Agent 的消息
            customer_message: 客户的消息
            current_stage: 当前 FSM 阶段
            conversation_history: 对话历史

        Returns:
            CoachFeedback: 教练反馈
        """
        logger.info(f"Evaluating response for stage: {current_stage.value}")

        # 1. 获取评估标准
        criteria = self.rubric.get_criteria(current_stage)

        # 2. 评估各维度
        dimension_scores = {}

        for criterion in criteria:
            score = self._evaluate_dimension(
                sales_message,
                customer_message,
                criterion,
                current_stage,
                conversation_history
            )
            dimension_scores[criterion.dimension.value] = score

        # 3. 计算总分
        overall_score = sum(
            dimension_scores.get(c.dimension.value, 0) * c.weight
            for c in criteria
        )

        # 4. 判断阶段对齐
        stage_alignment = self._check_stage_alignment(
            sales_message,
            current_stage,
            dimension_scores
        )

        # 5. 识别使用的技巧
        technique_used = self._identify_technique(
            sales_message,
            current_stage
        )

        # 6. 生成批评和建议
        critique, suggestion = self._generate_feedback(
            sales_message,
            customer_message,
            current_stage,
            dimension_scores
        )

        # 7. 识别优点和缺点
        strengths, weaknesses = self._identify_strengths_weaknesses(
            sales_message,
            current_stage,
            dimension_scores
        )

        return CoachFeedback(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            stage_alignment=stage_alignment,
            technique_used=technique_used,
            critique=critique,
            suggestion=suggestion,
            strengths=strengths,
            weaknesses=weaknesses
        )

    def _evaluate_dimension(
        self,
        sales_message: str,
        customer_message: str,
        criterion: EvaluationCriteria,
        current_stage: SalesState,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> float:
        """评估单个维度"""

        dimension = criterion.dimension

        # Methodology 评估
        if dimension == EvaluationDimension.METHODOLOGY:
            return self._evaluate_methodology(sales_message, current_stage)

        # Objection Handling 评估
        elif dimension == EvaluationDimension.OBJECTION_HANDLING:
            return self._evaluate_objection_handling(sales_message, customer_message)

        # Goal Orientation 评估
        elif dimension == EvaluationDimension.GOAL_ORIENTATION:
            return self._evaluate_goal_orientation(sales_message, current_stage)

        # Empathy 评估
        elif dimension == EvaluationDimension.EMPATHY:
            return self._evaluate_empathy(sales_message, customer_message)

        # Clarity 评估
        elif dimension == EvaluationDimension.CLARITY:
            return self._evaluate_clarity(sales_message)

        return 5.0  # 默认中等分数

    def _evaluate_methodology(self, sales_message: str, current_stage: SalesState) -> float:
        """评估方法论执行"""
        score = 5.0

        if current_stage == SalesState.DISCOVERY:
            # 检查是否使用 SPIN 提问
            spin_keywords = ["什么", "怎么", "如何", "为什么", "有没有", "能不能"]
            if any(keyword in sales_message for keyword in spin_keywords):
                score += 2.0

            # 检查是否是开放式问题
            if "？" in sales_message or "?" in sales_message:
                score += 1.0

            # 检查是否避免了直接推销
            sales_keywords = ["办理", "申请", "购买"]
            if not any(keyword in sales_message for keyword in sales_keywords):
                score += 1.0

        elif current_stage == SalesState.PITCH:
            # 检查是否使用 FAB 法则
            # Feature 关键词
            feature_keywords = ["额度", "年费", "权益", "积分", "功能"]
            has_feature = any(keyword in sales_message for keyword in feature_keywords)

            # Advantage 关键词
            advantage_keywords = ["比", "更", "高出", "优于", "超过"]
            has_advantage = any(keyword in sales_message for keyword in advantage_keywords)

            # Benefit 关键词
            benefit_keywords = ["您", "你", "意味着", "好处", "帮助"]
            has_benefit = any(keyword in sales_message for keyword in benefit_keywords)

            if has_feature:
                score += 1.5
            if has_advantage:
                score += 1.5
            if has_benefit:
                score += 2.0

        elif current_stage == SalesState.CLOSING:
            # 检查是否使用成交技巧
            closing_keywords = ["现在", "帮您", "开始", "办理", "申请", "流程"]
            if any(keyword in sales_message for keyword in closing_keywords):
                score += 3.0

        return min(10.0, score)

    def _evaluate_objection_handling(self, sales_message: str, customer_message: str) -> float:
        """评估异议处理"""
        score = 5.0

        # 检查客户是否提出异议
        objection_keywords = ["太贵", "不需要", "不相信", "考虑", "不感兴趣"]
        has_objection = any(keyword in customer_message for keyword in objection_keywords)

        if not has_objection:
            return 7.0  # 没有异议，给中上分数

        # 检查是否表现出同理心
        empathy_keywords = ["理解", "明白", "确实", "正常", "可以理解"]
        if any(keyword in sales_message for keyword in empathy_keywords):
            score += 2.0

        # 检查是否提供解决方案
        solution_keywords = ["其实", "实际上", "不过", "但是", "可以"]
        if any(keyword in sales_message for keyword in solution_keywords):
            score += 2.0

        # 检查是否避免了争辩
        argument_keywords = ["不对", "错了", "不是这样", "你误会了"]
        if not any(keyword in sales_message for keyword in argument_keywords):
            score += 1.0

        return min(10.0, score)

    def _evaluate_goal_orientation(self, sales_message: str, current_stage: SalesState) -> float:
        """评估目标推进力"""
        score = 5.0

        # 检查是否尝试推进对话
        if current_stage == SalesState.DISCOVERY:
            # 是否在收集信息
            if "？" in sales_message or "?" in sales_message:
                score += 3.0

        elif current_stage == SalesState.PITCH:
            # 是否在呈现价值
            value_keywords = ["权益", "优势", "好处", "帮助", "解决"]
            if any(keyword in sales_message for keyword in value_keywords):
                score += 3.0

        elif current_stage == SalesState.CLOSING:
            # 是否在推进成交
            action_keywords = ["办理", "申请", "开始", "现在", "帮您"]
            if any(keyword in sales_message for keyword in action_keywords):
                score += 3.0

        return min(10.0, score)

    def _evaluate_empathy(self, sales_message: str, customer_message: str) -> float:
        """评估同理心"""
        score = 5.0

        # 检查是否使用了同理心词汇
        empathy_keywords = ["理解", "明白", "确实", "您说得对", "我能体会"]
        if any(keyword in sales_message for keyword in empathy_keywords):
            score += 2.0

        # 检查是否使用了"您"而不是"你"
        if "您" in sales_message:
            score += 1.0

        # 检查是否避免了冷漠的表达
        cold_keywords = ["不行", "不可以", "没办法", "规定"]
        if not any(keyword in sales_message for keyword in cold_keywords):
            score += 2.0

        return min(10.0, score)

    def _evaluate_clarity(self, sales_message: str) -> float:
        """评估表达清晰度"""
        score = 5.0

        # 检查长度是否合适 (50-200字)
        length = len(sales_message)
        if 50 <= length <= 200:
            score += 2.0
        elif length > 200:
            score -= 1.0  # 太长扣分

        # 检查是否有结构 (使用了标点符号)
        if "，" in sales_message or "。" in sales_message:
            score += 1.0

        # 检查是否避免了专业术语堆砌
        jargon_keywords = ["APR", "CVV", "EMV", "POS"]
        if not any(keyword in sales_message for keyword in jargon_keywords):
            score += 2.0

        return min(10.0, score)

    def _check_stage_alignment(
        self,
        sales_message: str,
        current_stage: SalesState,
        dimension_scores: Dict[str, float]
    ) -> str:
        """检查阶段对齐"""

        # 获取方法论得分
        methodology_score = dimension_scores.get(EvaluationDimension.METHODOLOGY.value, 0)

        # 根据阶段判断
        if current_stage == SalesState.DISCOVERY:
            return "Pass" if methodology_score >= 7.0 else "Fail"
        elif current_stage == SalesState.PITCH:
            return "Pass" if methodology_score >= 7.0 else "Fail"
        elif current_stage == SalesState.OBJECTION:
            objection_score = dimension_scores.get(EvaluationDimension.OBJECTION_HANDLING.value, 0)
            return "Pass" if objection_score >= 7.0 else "Fail"
        else:
            return "Pass"

    def _identify_technique(self, sales_message: str, current_stage: SalesState) -> str:
        """识别使用的技巧"""

        if current_stage == SalesState.DISCOVERY:
            if "什么" in sales_message:
                return "SPIN - Situation Question"
            elif "痛点" in sales_message or "问题" in sales_message:
                return "SPIN - Problem Question"
            elif "影响" in sales_message:
                return "SPIN - Implication Question"
            elif "重要" in sales_message or "价值" in sales_message:
                return "SPIN - Need-Payoff Question"
            else:
                return "Open-ended Question"

        elif current_stage == SalesState.PITCH:
            has_fab = all(keyword in sales_message for keyword in ["额度", "比", "您"])
            if has_fab:
                return "FAB Presentation"
            else:
                return "Feature Description"

        elif current_stage == SalesState.OBJECTION:
            if "理解" in sales_message:
                return "Empathy + Solution"
            else:
                return "Direct Response"

        elif current_stage == SalesState.CLOSING:
            if "现在" in sales_message or "帮您" in sales_message:
                return "Assumptive Close"
            else:
                return "Trial Close"

        return "Unknown"

    def _generate_feedback(
        self,
        sales_message: str,
        customer_message: str,
        current_stage: SalesState,
        dimension_scores: Dict[str, float]
    ) -> tuple:
        """生成批评和建议"""

        critique = ""
        suggestion = ""

        # 根据阶段和得分生成反馈
        if current_stage == SalesState.DISCOVERY:
            methodology_score = dimension_scores.get(EvaluationDimension.METHODOLOGY.value, 0)

            if methodology_score < 7.0:
                critique = "Discovery 阶段应该使用 SPIN 提问法，但当前问题不够深入。"
                suggestion = "建议使用 SPIN 顺序提问：先了解现状 (Situation)，再挖掘痛点 (Problem)，然后放大影响 (Implication)，最后确认价值 (Need-Payoff)。"
            else:
                critique = "很好地使用了 SPIN 提问法，问题有深度。"
                suggestion = "继续保持，可以根据客户回答追问更多细节。"

        elif current_stage == SalesState.PITCH:
            methodology_score = dimension_scores.get(EvaluationDimension.METHODOLOGY.value, 0)

            if methodology_score < 7.0:
                critique = "Pitch 阶段应该使用 FAB 法则，但当前只说了产品特性，没有转化为客户利益。"
                suggestion = "建议使用 FAB 结构：先说特性 (Feature)，再说优势 (Advantage)，最后说利益 (Benefit)。例如：'我们的额度50万（特性），比普通卡高5倍（优势），这意味着您大额消费时不用担心额度不够（利益）。'"
            else:
                critique = "很好地使用了 FAB 法则，清晰地表达了客户利益。"
                suggestion = "继续保持，可以增加具体的案例或数字来增强说服力。"

        elif current_stage == SalesState.OBJECTION:
            objection_score = dimension_scores.get(EvaluationDimension.OBJECTION_HANDLING.value, 0)
            empathy_score = dimension_scores.get(EvaluationDimension.EMPATHY.value, 0)

            if empathy_score < 7.0:
                critique = "面对客户异议时，同理心不足，容易让客户感觉被忽视。"
                suggestion = "建议先表达理解和认同，再提供解决方案。例如：'我理解您对价格的顾虑，这是很正常的。实际上...'"
            elif objection_score < 7.0:
                critique = "虽然表现出了同理心，但解决方案不够有力。"
                suggestion = "建议提供具体的证据或案例来支持解决方案，增强说服力。"
            else:
                critique = "很好地处理了客户异议，既有同理心又有解决方案。"
                suggestion = "继续保持，可以尝试将异议转化为优势。"

        return critique, suggestion

    def _identify_strengths_weaknesses(
        self,
        sales_message: str,
        current_stage: SalesState,
        dimension_scores: Dict[str, float]
    ) -> tuple:
        """识别优点和缺点"""

        strengths = []
        weaknesses = []

        for dimension, score in dimension_scores.items():
            if score >= 8.0:
                strengths.append(f"{dimension}: {score:.1f}/10 (优秀)")
            elif score < 6.0:
                weaknesses.append(f"{dimension}: {score:.1f}/10 (需改进)")

        if not strengths:
            strengths.append("表达基本清晰")

        if not weaknesses:
            weaknesses.append("无明显缺点")

        return strengths, weaknesses


# ============================================================================
# 测试和演示
# ============================================================================

def demo_sales_coach():
    """演示销售教练"""
    print("=" * 80)
    print("Phase 3B Week 6 Day 3-4: Sales Coach Demo")
    print("=" * 80)

    coach = SalesCoach()

    # 测试场景
    test_cases = [
        {
            "stage": SalesState.DISCOVERY,
            "customer": "我想了解一下信用卡",
            "sales_good": "您目前使用信用卡的主要场景是什么？比如是用于日常消费还是商务出差？",
            "sales_bad": "我们的白金卡额度高达50万，年费首年免费！"
        },
        {
            "stage": SalesState.PITCH,
            "customer": "额度多少？",
            "sales_good": "我们的白金卡最高额度可达50万，比市面上普通信用卡的5-10万额度高出5倍，这意味着您在大额消费时不用担心额度不够。",
            "sales_bad": "额度50万。"
        },
        {
            "stage": SalesState.OBJECTION,
            "customer": "太贵了，年费1000元我接受不了",
            "sales_good": "我理解您对成本的关注，这是很正常的。实际上，首年免年费，次年刷满6笔即可免年费，您可以零成本体验高端卡的所有权益。",
            "sales_bad": "这个价格已经很便宜了，其他银行更贵。"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"Test Case {i}: {case['stage'].value.upper()} Stage")
        print("=" * 80)

        print(f"\nCustomer: {case['customer']}")

        # 测试好的响应
        print("\n[Good Response]")
        print(f"Sales: {case['sales_good']}")

        feedback = coach.evaluate_response(
            sales_message=case['sales_good'],
            customer_message=case['customer'],
            current_stage=case['stage']
        )

        print("\nCoach Feedback:")
        print(f"  Overall Score: {feedback.overall_score:.1f}/10")
        print(f"  Stage Alignment: {feedback.stage_alignment}")
        print(f"  Technique Used: {feedback.technique_used}")
        print("  Dimension Scores:")
        for dim, score in feedback.dimension_scores.items():
            print(f"    - {dim}: {score:.1f}/10")
        print(f"  Critique: {feedback.critique}")
        print(f"  Suggestion: {feedback.suggestion}")
        print(f"  Strengths: {', '.join(feedback.strengths)}")
        print(f"  Weaknesses: {', '.join(feedback.weaknesses)}")

        # 测试坏的响应
        print("\n[Bad Response]")
        print(f"Sales: {case['sales_bad']}")

        feedback = coach.evaluate_response(
            sales_message=case['sales_bad'],
            customer_message=case['customer'],
            current_stage=case['stage']
        )

        print("\nCoach Feedback:")
        print(f"  Overall Score: {feedback.overall_score:.1f}/10")
        print(f"  Stage Alignment: {feedback.stage_alignment}")
        print(f"  Technique Used: {feedback.technique_used}")
        print(f"  Critique: {feedback.critique}")
        print(f"  Suggestion: {feedback.suggestion}")

    print("\n" + "=" * 80)
    print("[OK] Demo completed successfully!")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行演示
    demo_sales_coach()
