"""
Phase 3B Week 7 Day 5-6: Real-time Interruption Handling with VAD

核心目标：
1. 实现实时打断检测
2. 集成 VAD 进行语音活动检测
3. 实现对话状态管理（说话中/静音中）
4. 实现打断恢复机制

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import time
from enum import Enum
from typing import Dict, Optional, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState

logger = logging.getLogger(__name__)


class ConversationRole(str, Enum):
    """对话角色"""
    AGENT = "agent"
    USER = "user"


class SpeechState(str, Enum):
    """语音状态"""
    IDLE = "idle"              # 空闲
    AGENT_SPEAKING = "agent_speaking"  # Agent 说话中
    USER_SPEAKING = "user_speaking"    # 用户说话中
    INTERRUPTED = "interrupted"        # 被打断


@dataclass
class InterruptionEvent:
    """打断事件"""
    timestamp: float
    interrupted_role: ConversationRole
    interrupted_text: str
    interrupted_at_position: int  # 被打断的位置（字符数）
    user_input: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "interrupted_role": self.interrupted_role.value,
            "interrupted_text": self.interrupted_text,
            "interrupted_at_position": self.interrupted_at_position,
            "user_input": self.user_input
        }


@dataclass
class ConversationTurn:
    """对话轮次"""
    turn_id: int
    role: ConversationRole
    text: str
    start_time: float
    end_time: float
    interrupted: bool = False
    interruption_event: Optional[InterruptionEvent] = None

    @property
    def duration(self) -> float:
        """持续时间"""
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "turn_id": self.turn_id,
            "role": self.role.value,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "interrupted": self.interrupted,
            "interruption_event": self.interruption_event.to_dict() if self.interruption_event else None
        }


class InterruptionDetector:
    """打断检测器"""

    def __init__(
        self,
        silence_threshold: float = 0.5,  # 静音阈值（秒）
        speech_threshold: float = 0.3,   # 语音阈值（秒）
    ):
        self.silence_threshold = silence_threshold
        self.speech_threshold = speech_threshold

        self.current_state = SpeechState.IDLE
        self.last_speech_time = 0.0
        self.last_silence_time = 0.0

        logger.info(
            f"InterruptionDetector initialized: "
            f"silence_threshold={silence_threshold}s, "
            f"speech_threshold={speech_threshold}s"
        )

    def on_speech_detected(self, role: ConversationRole) -> bool:
        """检测到语音"""
        current_time = time.time()
        self.last_speech_time = current_time

        # 检测打断
        if self.current_state == SpeechState.AGENT_SPEAKING and role == ConversationRole.USER:
            logger.info("Interruption detected: User interrupted Agent")
            self.current_state = SpeechState.INTERRUPTED
            return True

        elif self.current_state == SpeechState.USER_SPEAKING and role == ConversationRole.AGENT:
            logger.info("Interruption detected: Agent interrupted User")
            self.current_state = SpeechState.INTERRUPTED
            return True

        # 更新状态
        if role == ConversationRole.AGENT:
            self.current_state = SpeechState.AGENT_SPEAKING
        else:
            self.current_state = SpeechState.USER_SPEAKING

        return False

    def on_silence_detected(self) -> bool:
        """检测到静音"""
        current_time = time.time()
        self.last_silence_time = current_time

        # 检查是否超过静音阈值
        if current_time - self.last_speech_time > self.silence_threshold:
            if self.current_state != SpeechState.IDLE:
                logger.info("Silence detected, returning to IDLE")
                self.current_state = SpeechState.IDLE
                return True

        return False

    def reset(self):
        """重置状态"""
        self.current_state = SpeechState.IDLE
        self.last_speech_time = 0.0
        self.last_silence_time = 0.0
        logger.info("InterruptionDetector reset")


class InterruptionHandler:
    """打断处理器"""

    def __init__(
        self,
        enable_recovery: bool = True,
        max_recovery_attempts: int = 3
    ):
        self.enable_recovery = enable_recovery
        self.max_recovery_attempts = max_recovery_attempts

        self.interruption_history: List[InterruptionEvent] = []
        self.recovery_attempts = 0

        logger.info(
            f"InterruptionHandler initialized: "
            f"recovery_enabled={enable_recovery}, "
            f"max_recovery_attempts={max_recovery_attempts}"
        )

    async def handle_interruption(
        self,
        event: InterruptionEvent,
        on_recovery: Optional[Callable] = None
    ) -> bool:
        """处理打断事件"""
        logger.info(
            f"Handling interruption: role={event.interrupted_role.value}, "
            f"position={event.interrupted_at_position}/{len(event.interrupted_text)}"
        )

        # 记录打断事件
        self.interruption_history.append(event)

        # 恢复策略
        if self.enable_recovery and self.recovery_attempts < self.max_recovery_attempts:
            self.recovery_attempts += 1

            logger.info(f"Attempting recovery ({self.recovery_attempts}/{self.max_recovery_attempts})")

            if on_recovery:
                await on_recovery(event)

            return True

        else:
            logger.warning("Max recovery attempts reached or recovery disabled")
            return False

    def get_interruption_stats(self) -> Dict[str, Any]:
        """获取打断统计"""
        total = len(self.interruption_history)

        if total == 0:
            return {
                "total_interruptions": 0,
                "agent_interrupted": 0,
                "user_interrupted": 0,
                "recovery_attempts": 0
            }

        agent_interrupted = sum(
            1 for e in self.interruption_history
            if e.interrupted_role == ConversationRole.AGENT
        )

        user_interrupted = sum(
            1 for e in self.interruption_history
            if e.interrupted_role == ConversationRole.USER
        )

        return {
            "total_interruptions": total,
            "agent_interrupted": agent_interrupted,
            "user_interrupted": user_interrupted,
            "recovery_attempts": self.recovery_attempts
        }

    def reset(self):
        """重置状态"""
        self.interruption_history.clear()
        self.recovery_attempts = 0
        logger.info("InterruptionHandler reset")


class ConversationStateManager:
    """对话状态管理器"""

    def __init__(self):
        self.turns: List[ConversationTurn] = []
        self.current_turn: Optional[ConversationTurn] = None
        self.turn_counter = 0

        self.detector = InterruptionDetector()
        self.handler = InterruptionHandler()

        logger.info("ConversationStateManager initialized")

    async def start_turn(
        self,
        role: ConversationRole,
        text: str
    ) -> ConversationTurn:
        """开始新的对话轮次"""
        self.turn_counter += 1

        turn = ConversationTurn(
            turn_id=self.turn_counter,
            role=role,
            text=text,
            start_time=time.time(),
            end_time=0.0
        )

        self.current_turn = turn

        logger.info(f"Started turn {turn.turn_id}: {role.value}")

        # 检测打断
        is_interrupted = self.detector.on_speech_detected(role)

        if is_interrupted and len(self.turns) > 0:
            # 标记上一轮被打断
            prev_turn = self.turns[-1]
            prev_turn.interrupted = True
            prev_turn.end_time = time.time()

            # 创建打断事件
            event = InterruptionEvent(
                timestamp=time.time(),
                interrupted_role=prev_turn.role,
                interrupted_text=prev_turn.text,
                interrupted_at_position=len(prev_turn.text),
                user_input=text if role == ConversationRole.USER else ""
            )

            prev_turn.interruption_event = event

            # 处理打断
            await self.handler.handle_interruption(event)

        return turn

    async def end_turn(self):
        """结束当前对话轮次"""
        if self.current_turn:
            self.current_turn.end_time = time.time()
            self.turns.append(self.current_turn)

            logger.info(
                f"Ended turn {self.current_turn.turn_id}: "
                f"duration={self.current_turn.duration:.2f}s"
            )

            self.current_turn = None

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return [turn.to_dict() for turn in self.turns]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_turns = len(self.turns)

        if total_turns == 0:
            return {
                "total_turns": 0,
                "agent_turns": 0,
                "user_turns": 0,
                "interrupted_turns": 0,
                "average_turn_duration": 0.0,
                "interruption_stats": self.handler.get_interruption_stats()
            }

        agent_turns = sum(1 for t in self.turns if t.role == ConversationRole.AGENT)
        user_turns = sum(1 for t in self.turns if t.role == ConversationRole.USER)
        interrupted_turns = sum(1 for t in self.turns if t.interrupted)

        avg_duration = sum(t.duration for t in self.turns) / total_turns

        return {
            "total_turns": total_turns,
            "agent_turns": agent_turns,
            "user_turns": user_turns,
            "interrupted_turns": interrupted_turns,
            "interruption_rate": interrupted_turns / total_turns if total_turns > 0 else 0,
            "average_turn_duration": avg_duration,
            "interruption_stats": self.handler.get_interruption_stats()
        }

    def reset(self):
        """重置状态"""
        self.turns.clear()
        self.current_turn = None
        self.turn_counter = 0
        self.detector.reset()
        self.handler.reset()
        logger.info("ConversationStateManager reset")


# ============================================================================
# 演示和测试
# ============================================================================

async def demo_basic_conversation():
    """演示基本对话"""
    print("\n" + "=" * 80)
    print("Basic Conversation Demo")
    print("=" * 80)

    manager = ConversationStateManager()

    # 模拟对话
    conversations = [
        (ConversationRole.AGENT, "您好！我是XX银行的销售顾问，很高兴为您服务。"),
        (ConversationRole.USER, "你好，我想了解一下信用卡。"),
        (ConversationRole.AGENT, "好的，请问您目前使用信用卡的主要场景是什么？"),
        (ConversationRole.USER, "主要是日常消费和网购。"),
        (ConversationRole.AGENT, "明白了。我们的白金卡最高额度可达50万..."),
    ]

    for role, text in conversations:
        print(f"\n[{role.value}] {text}")

        await manager.start_turn(role, text)
        await asyncio.sleep(0.5)  # 模拟说话时间
        await manager.end_turn()

    # 打印统计
    stats = manager.get_statistics()
    print("\n" + "-" * 80)
    print("Statistics:")
    print(f"  Total Turns: {stats['total_turns']}")
    print(f"  Agent Turns: {stats['agent_turns']}")
    print(f"  User Turns: {stats['user_turns']}")
    print(f"  Interrupted Turns: {stats['interrupted_turns']}")
    print(f"  Average Turn Duration: {stats['average_turn_duration']:.2f}s")


async def demo_interruption_handling():
    """演示打断处理"""
    print("\n" + "=" * 80)
    print("Interruption Handling Demo")
    print("=" * 80)

    manager = ConversationStateManager()

    # 模拟对话（包含打断）
    print("\n[Scenario] User interrupts Agent")

    # Agent 开始说话
    print("\n[Agent] 我们的白金卡最高额度可达50万，比市面上...")
    await manager.start_turn(
        ConversationRole.AGENT,
        "我们的白金卡最高额度可达50万，比市面上普通信用卡的5-10万额度高出5倍"
    )

    # 模拟 Agent 说话中
    await asyncio.sleep(0.3)

    # 用户打断
    print("[User] (interrupts) 等等，年费多少？")
    await manager.end_turn()  # 结束 Agent 的轮次

    await manager.start_turn(
        ConversationRole.USER,
        "等等，年费多少？"
    )
    await asyncio.sleep(0.2)
    await manager.end_turn()

    # Agent 回应打断
    print("[Agent] 首年免年费，次年刷满6笔即可免年费。")
    await manager.start_turn(
        ConversationRole.AGENT,
        "首年免年费，次年刷满6笔即可免年费。"
    )
    await asyncio.sleep(0.3)
    await manager.end_turn()

    # 打印统计
    stats = manager.get_statistics()
    print("\n" + "-" * 80)
    print("Statistics:")
    print(f"  Total Turns: {stats['total_turns']}")
    print(f"  Interrupted Turns: {stats['interrupted_turns']}")
    print(f"  Interruption Rate: {stats['interruption_rate']*100:.1f}%")

    interruption_stats = stats['interruption_stats']
    print(f"\n  Interruption Details:")
    print(f"    Total: {interruption_stats['total_interruptions']}")
    print(f"    Agent Interrupted: {interruption_stats['agent_interrupted']}")
    print(f"    User Interrupted: {interruption_stats['user_interrupted']}")
    print(f"    Recovery Attempts: {interruption_stats['recovery_attempts']}")


async def demo_conversation_history():
    """演示对话历史"""
    print("\n" + "=" * 80)
    print("Conversation History Demo")
    print("=" * 80)

    manager = ConversationStateManager()

    # 模拟对话
    conversations = [
        (ConversationRole.AGENT, "您好！"),
        (ConversationRole.USER, "你好。"),
        (ConversationRole.AGENT, "请问您对信用卡有什么需求吗？"),
        (ConversationRole.USER, "我想办一张额度高的卡。"),
    ]

    for role, text in conversations:
        await manager.start_turn(role, text)
        await asyncio.sleep(0.2)
        await manager.end_turn()

    # 打印历史
    history = manager.get_conversation_history()

    print("\nConversation History:")
    for turn in history:
        print(f"\n  Turn {turn['turn_id']}:")
        print(f"    Role: {turn['role']}")
        print(f"    Text: {turn['text']}")
        print(f"    Duration: {turn['duration']:.2f}s")
        print(f"    Interrupted: {turn['interrupted']}")


async def demo_multiple_interruptions():
    """演示多次打断"""
    print("\n" + "=" * 80)
    print("Multiple Interruptions Demo")
    print("=" * 80)

    manager = ConversationStateManager()

    # 模拟多次打断的对话
    print("\n[Scenario] Multiple interruptions")

    # Turn 1: Agent starts
    print("\n[Agent] 我们的白金卡有很多优势...")
    await manager.start_turn(ConversationRole.AGENT, "我们的白金卡有很多优势...")
    await asyncio.sleep(0.2)
    await manager.end_turn()

    # Turn 2: User interrupts
    print("[User] (interrupts) 年费多少？")
    await manager.start_turn(ConversationRole.USER, "年费多少？")
    await asyncio.sleep(0.1)
    await manager.end_turn()

    # Turn 3: Agent responds
    print("[Agent] 首年免年费...")
    await manager.start_turn(ConversationRole.AGENT, "首年免年费...")
    await asyncio.sleep(0.2)
    await manager.end_turn()

    # Turn 4: User interrupts again
    print("[User] (interrupts) 额度呢？")
    await manager.start_turn(ConversationRole.USER, "额度呢？")
    await asyncio.sleep(0.1)
    await manager.end_turn()

    # Turn 5: Agent responds
    print("[Agent] 最高50万额度。")
    await manager.start_turn(ConversationRole.AGENT, "最高50万额度。")
    await asyncio.sleep(0.2)
    await manager.end_turn()

    # 打印统计
    stats = manager.get_statistics()
    print("\n" + "-" * 80)
    print("Statistics:")
    print(f"  Total Turns: {stats['total_turns']}")
    print(f"  Interrupted Turns: {stats['interrupted_turns']}")
    print(f"  Interruption Rate: {stats['interruption_rate']*100:.1f}%")

    interruption_stats = stats['interruption_stats']
    print(f"\n  Interruption Details:")
    print(f"    Total: {interruption_stats['total_interruptions']}")
    print(f"    Agent Interrupted: {interruption_stats['agent_interrupted']}")
    print(f"    Recovery Attempts: {interruption_stats['recovery_attempts']}")


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

    print("\n" + "=" * 80)
    print("Phase 3B Week 7 Day 5-6: Real-time Interruption Handling")
    print("=" * 80)

    # 1. 演示基本对话
    await demo_basic_conversation()

    # 2. 演示打断处理
    await demo_interruption_handling()

    # 3. 演示对话历史
    await demo_conversation_history()

    # 4. 演示多次打断
    await demo_multiple_interruptions()

    print("\n" + "=" * 80)
    print("All demos completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
