"""
Phase 3B Week 6 Day 1-2: User Simulator Agent

核心目标：构建多种客户人格，为 Sales Agent 提供对抗性训练。

客户人格类型：
1. PRICE_SENSITIVE: 价格敏感型 - "太贵了"
2. SKEPTICAL: 怀疑挑剔型 - "我不相信"
3. SILENT: 沉默寡言型 - "嗯"、"哦"
4. BUSY: 忙碌型 - "我很忙，长话短说"
5. INTERESTED: 感兴趣型 - "听起来不错"
6. COMPARISON: 对比型 - "和XX银行比怎么样"

实现日期: 2026-02-02
"""

import logging
import sys
import os
import random
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class CustomerPersonality(str, Enum):
    """客户人格类型"""
    PRICE_SENSITIVE = "price_sensitive"      # 价格敏感型
    SKEPTICAL = "skeptical"                  # 怀疑挑剔型
    SILENT = "silent"                        # 沉默寡言型
    BUSY = "busy"                            # 忙碌型
    INTERESTED = "interested"                # 感兴趣型
    COMPARISON = "comparison"                # 对比型


@dataclass
class PersonalityProfile:
    """人格档案"""
    personality: CustomerPersonality
    name: str
    description: str
    objection_rate: float  # 异议概率 (0-1)
    engagement_level: float  # 参与度 (0-1)
    typical_objections: List[str]
    typical_responses: List[str]
    buying_threshold: int  # 需要多少轮才可能购买


class PersonalityLibrary:
    """人格库"""

    def __init__(self):
        self.profiles: Dict[CustomerPersonality, PersonalityProfile] = {}
        self._initialize_profiles()

    def _initialize_profiles(self):
        """初始化人格档案"""

        # 1. 价格敏感型
        self.profiles[CustomerPersonality.PRICE_SENSITIVE] = PersonalityProfile(
            personality=CustomerPersonality.PRICE_SENSITIVE,
            name="价格敏感型客户",
            description="对价格极度敏感，总是觉得太贵，喜欢讨价还价",
            objection_rate=0.8,
            engagement_level=0.6,
            typical_objections=[
                "太贵了，能便宜点吗？",
                "年费这么高，不划算啊",
                "其他银行的卡都免年费，你们为什么要收？",
                "有没有优惠活动？",
                "这个价格我接受不了"
            ],
            typical_responses=[
                "嗯，听起来还行，但是价格...",
                "功能是不错，就是太贵了",
                "我再看看其他家的价格",
                "能不能给我打个折？"
            ],
            buying_threshold=8  # 需要8轮才可能购买
        )

        # 2. 怀疑挑剔型
        self.profiles[CustomerPersonality.SKEPTICAL] = PersonalityProfile(
            personality=CustomerPersonality.SKEPTICAL,
            name="怀疑挑剔型客户",
            description="对一切持怀疑态度，喜欢挑毛病，不轻易相信",
            objection_rate=0.9,
            engagement_level=0.7,
            typical_objections=[
                "我不相信，你们肯定有坑",
                "说得这么好，肯定有隐藏费用",
                "你们的服务靠谱吗？",
                "我听说你们银行有很多投诉",
                "这些权益真的能兑现吗？",
                "会不会有什么陷阱？"
            ],
            typical_responses=[
                "我需要看看合同条款",
                "你说的这些我都不太相信",
                "有什么证据证明你说的是真的？",
                "我要先查查你们银行的口碑"
            ],
            buying_threshold=10  # 需要10轮才可能购买
        )

        # 3. 沉默寡言型
        self.profiles[CustomerPersonality.SILENT] = PersonalityProfile(
            personality=CustomerPersonality.SILENT,
            name="沉默寡言型客户",
            description="话很少，只用简短的词回应，很难判断想法",
            objection_rate=0.3,
            engagement_level=0.3,
            typical_objections=[
                "不需要",
                "不感兴趣",
                "算了"
            ],
            typical_responses=[
                "嗯",
                "哦",
                "是吗",
                "知道了",
                "...",
                "好吧",
                "随便"
            ],
            buying_threshold=6  # 需要6轮才可能购买
        )

        # 4. 忙碌型
        self.profiles[CustomerPersonality.BUSY] = PersonalityProfile(
            personality=CustomerPersonality.BUSY,
            name="忙碌型客户",
            description="时间紧张，希望快速了解核心信息，不喜欢啰嗦",
            objection_rate=0.5,
            engagement_level=0.5,
            typical_objections=[
                "我很忙，长话短说",
                "直接说重点",
                "别废话了，有什么优惠？",
                "我没时间听这些"
            ],
            typical_responses=[
                "快点说",
                "然后呢？",
                "还有吗？",
                "就这些？",
                "知道了，我考虑一下"
            ],
            buying_threshold=4  # 需要4轮就可能购买（如果说服力强）
        )

        # 5. 感兴趣型
        self.profiles[CustomerPersonality.INTERESTED] = PersonalityProfile(
            personality=CustomerPersonality.INTERESTED,
            name="感兴趣型客户",
            description="对产品感兴趣，愿意了解，但需要更多信息才能决定",
            objection_rate=0.3,
            engagement_level=0.8,
            typical_objections=[
                "听起来不错，但我想再了解一下",
                "还有什么其他权益吗？",
                "申请流程复杂吗？"
            ],
            typical_responses=[
                "听起来不错",
                "这个挺好的",
                "还有什么权益？",
                "能详细说说吗？",
                "我挺感兴趣的",
                "继续说"
            ],
            buying_threshold=3  # 需要3轮就可能购买
        )

        # 6. 对比型
        self.profiles[CustomerPersonality.COMPARISON] = PersonalityProfile(
            personality=CustomerPersonality.COMPARISON,
            name="对比型客户",
            description="喜欢对比不同产品，理性分析，需要看到明显优势",
            objection_rate=0.6,
            engagement_level=0.7,
            typical_objections=[
                "和招商银行的卡比怎么样？",
                "工商银行的卡年费更低",
                "为什么我要选你们而不是其他银行？",
                "你们的优势在哪里？"
            ],
            typical_responses=[
                "我需要对比一下",
                "其他银行也有类似的产品",
                "你们和XX银行比有什么优势？",
                "我再看看其他选择"
            ],
            buying_threshold=5  # 需要5轮才可能购买
        )

        logger.info(f"Initialized {len(self.profiles)} customer personality profiles")

    def get_profile(self, personality: CustomerPersonality) -> PersonalityProfile:
        """获取人格档案"""
        return self.profiles[personality]

    def get_random_profile(self) -> PersonalityProfile:
        """随机获取一个人格档案"""
        personality = random.choice(list(CustomerPersonality))
        return self.profiles[personality]


class UserSimulator:
    """
    用户模拟器 Agent

    核心功能：
    1. 根据人格档案生成响应
    2. 模拟各种客户行为
    3. 提供对抗性训练
    """

    def __init__(self, personality: Optional[CustomerPersonality] = None):
        """
        初始化用户模拟器

        Args:
            personality: 客户人格类型（如果为 None，则随机选择）
        """
        self.personality_library = PersonalityLibrary()

        if personality:
            self.profile = self.personality_library.get_profile(personality)
        else:
            self.profile = self.personality_library.get_random_profile()

        self.turn_count = 0
        self.objections_raised = []
        self.interest_level = 0.0  # 兴趣度 (0-1)

        logger.info(f"UserSimulator initialized with personality: {self.profile.name}")

    def generate_response(
        self,
        sales_message: str,
        sales_state: str = "unknown"
    ) -> Dict[str, Any]:
        """
        生成客户响应

        Args:
            sales_message: 销售人员的消息
            sales_state: 当前销售阶段

        Returns:
            响应字典
        """
        self.turn_count += 1

        # 1. 决定是否提出异议
        should_object = random.random() < self.profile.objection_rate

        # 2. 根据人格和阶段生成响应
        if self.profile.personality == CustomerPersonality.PRICE_SENSITIVE:
            response = self._generate_price_sensitive_response(
                sales_message, sales_state, should_object
            )

        elif self.profile.personality == CustomerPersonality.SKEPTICAL:
            response = self._generate_skeptical_response(
                sales_message, sales_state, should_object
            )

        elif self.profile.personality == CustomerPersonality.SILENT:
            response = self._generate_silent_response(
                sales_message, sales_state, should_object
            )

        elif self.profile.personality == CustomerPersonality.BUSY:
            response = self._generate_busy_response(
                sales_message, sales_state, should_object
            )

        elif self.profile.personality == CustomerPersonality.INTERESTED:
            response = self._generate_interested_response(
                sales_message, sales_state, should_object
            )

        elif self.profile.personality == CustomerPersonality.COMPARISON:
            response = self._generate_comparison_response(
                sales_message, sales_state, should_object
            )

        else:
            response = {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

        # 3. 更新兴趣度
        self._update_interest_level(response)

        # 4. 判断是否达到购买阈值
        if self.turn_count >= self.profile.buying_threshold and self.interest_level > 0.6:
            if random.random() < 0.3:  # 30% 概率发出购买信号
                response["buying_signal"] = True
                response["content"] = random.choice([
                    "好的，我要办理",
                    "那就办一张吧",
                    "听起来不错，怎么申请？",
                    "可以，帮我办理吧"
                ])

        return response

    def _generate_price_sensitive_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成价格敏感型响应"""

        # 检测是否提到价格
        price_keywords = ["年费", "费用", "价格", "多少钱", "成本"]
        mentions_price = any(keyword in sales_message for keyword in price_keywords)

        if mentions_price or should_object:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _generate_skeptical_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成怀疑挑剔型响应"""

        # 总是持怀疑态度
        if should_object or self.turn_count < 5:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _generate_silent_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成沉默寡言型响应"""

        if should_object:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            # 大部分时候只说简短的词
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _generate_busy_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成忙碌型响应"""

        # 如果销售人员说话太长，表示不耐烦
        if len(sales_message) > 100:
            return {
                "content": "太长了，简单说",
                "objection": True,
                "buying_signal": False
            }

        if should_object:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _generate_interested_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成感兴趣型响应"""

        # 大部分时候表现出兴趣
        if should_object:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _generate_comparison_response(
        self, sales_message: str, sales_state: str, should_object: bool
    ) -> Dict[str, Any]:
        """生成对比型响应"""

        if should_object:
            objection = random.choice(self.profile.typical_objections)
            self.objections_raised.append(objection)
            return {
                "content": objection,
                "objection": True,
                "buying_signal": False
            }
        else:
            return {
                "content": random.choice(self.profile.typical_responses),
                "objection": False,
                "buying_signal": False
            }

    def _update_interest_level(self, response: Dict[str, Any]):
        """更新兴趣度"""
        if response.get("objection"):
            self.interest_level = max(0, self.interest_level - 0.1)
        else:
            self.interest_level = min(1.0, self.interest_level + 0.15)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "personality": self.profile.personality.value,
            "personality_name": self.profile.name,
            "turn_count": self.turn_count,
            "objections_raised": len(self.objections_raised),
            "interest_level": self.interest_level,
            "buying_threshold": self.profile.buying_threshold,
            "ready_to_buy": self.turn_count >= self.profile.buying_threshold and self.interest_level > 0.6
        }


# ============================================================================
# 测试和演示
# ============================================================================

def demo_user_simulator():
    """演示用户模拟器"""
    print("=" * 80)
    print("Phase 3B Week 6 Day 1-2: User Simulator Demo")
    print("=" * 80)

    # 测试所有人格类型
    personalities = list(CustomerPersonality)

    for personality in personalities:
        print(f"\n{'=' * 80}")
        print(f"Testing Personality: {personality.value}")
        print("=" * 80)

        simulator = UserSimulator(personality=personality)
        profile = simulator.profile

        print("\nProfile:")
        print(f"  Name: {profile.name}")
        print(f"  Description: {profile.description}")
        print(f"  Objection Rate: {profile.objection_rate:.0%}")
        print(f"  Engagement Level: {profile.engagement_level:.0%}")
        print(f"  Buying Threshold: {profile.buying_threshold} turns")

        # 模拟5轮对话
        print("\nSimulating 5 turns:")
        sales_messages = [
            "您好！我是XX银行的销售顾问，很高兴为您服务。",
            "我们的白金卡最高额度可达50万，比普通卡高5倍。",
            "年费首年免费，次年刷满6笔即可免年费。",
            "全球1200+机场贵宾厅免费使用。",
            "那我现在帮您办理，需要您提供一下身份证信息。"
        ]

        for i, sales_msg in enumerate(sales_messages, 1):
            print(f"\n  Turn {i}:")
            print(f"    Sales: {sales_msg}")

            response = simulator.generate_response(sales_msg, sales_state="pitch")

            print(f"    Customer: {response['content']}")
            print(f"    Objection: {response['objection']}")
            print(f"    Buying Signal: {response['buying_signal']}")

        # 统计信息
        stats = simulator.get_stats()
        print("\n  Stats:")
        print(f"    Turns: {stats['turn_count']}")
        print(f"    Objections: {stats['objections_raised']}")
        print(f"    Interest Level: {stats['interest_level']:.2f}")
        print(f"    Ready to Buy: {stats['ready_to_buy']}")

    print("\n" + "=" * 80)
    print("[OK] Demo completed successfully!")


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行演示
    demo_user_simulator()
