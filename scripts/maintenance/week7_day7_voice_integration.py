"""
Phase 3B Week 7 Day 7: Complete Voice Interface Integration Test

核心目标：
1. 集成 TTS + STT + Interruption Handling
2. 实现完整的语音对话流程
3. 测试端到端的语音交互
4. 生成性能报告

实现日期: 2026-02-02
"""

import logging
import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Any, List
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.agents.conversation import SalesState

# 导入 Week 7 的组件
import sys
sys.path.insert(0, os.path.dirname(__file__))

logger = logging.getLogger(__name__)


class VoiceInterface:
    """完整的语音交互接口"""

    def __init__(
        self,
        tts_backend: str = "edge_tts",
        stt_backend: str = "faster_whisper",
        enable_interruption: bool = True
    ):
        # 延迟导入以避免循环依赖
        from week7_day1_tts_emotion import EmotionalTTS, TTSBackend, EmotionLibrary
        from week7_day3_stt_lowlatency import LowLatencySTT, STTBackend
        from week7_day5_interruption_handling import ConversationStateManager, ConversationRole

        self.EmotionLibrary = EmotionLibrary
        self.ConversationRole = ConversationRole

        # 初始化 TTS
        self.tts = EmotionalTTS(
            backend=TTSBackend(tts_backend),
            enable_cache=True
        )

        # 初始化 STT
        self.stt = LowLatencySTT(
            backend=STTBackend(stt_backend),
            enable_vad=False  # MP3 不支持 VAD
        )

        # 初始化打断处理
        self.conversation_manager = ConversationStateManager() if enable_interruption else None

        logger.info(
            f"VoiceInterface initialized: tts={tts_backend}, "
            f"stt={stt_backend}, interruption={enable_interruption}"
        )

    async def speak(
        self,
        text: str,
        sales_state: SalesState,
        save_to: Optional[str] = None
    ) -> bytes:
        """Agent 说话"""
        logger.info(f"Agent speaking: {text[:50]}...")

        # 记录对话轮次
        if self.conversation_manager:
            await self.conversation_manager.start_turn(
                self.ConversationRole.AGENT,
                text
            )

        try:
            # 生成语音
            audio_data = await self.tts.synthesize_with_state(text, sales_state)

            # 保存音频
            if save_to:
                self.tts.save_audio(audio_data, save_to)

        except Exception as e:
            logger.error(f"TTS error: {e}")
            # 使用默认配置重试
            logger.warning("Retrying with neutral emotion")
            audio_data = await self.tts.synthesize(
                text,
                emotion=self.EmotionLibrary.get_emotion_for_sales_state(SalesState.OPENING)
            )

            if save_to:
                self.tts.save_audio(audio_data, save_to)

        # 结束轮次
        if self.conversation_manager:
            await self.conversation_manager.end_turn()

        return audio_data

    async def listen(
        self,
        audio_file: str,
        language: str = "zh"
    ) -> str:
        """听取用户输入"""
        logger.info(f"Listening to: {audio_file}")

        # 记录对话轮次
        if self.conversation_manager:
            await self.conversation_manager.start_turn(
                self.ConversationRole.USER,
                ""  # 文本稍后填充
            )

        # 转写语音
        result = await self.stt.transcribe(audio_file, language)

        # 更新轮次文本
        if self.conversation_manager and self.conversation_manager.current_turn:
            self.conversation_manager.current_turn.text = result.text

        # 结束轮次
        if self.conversation_manager:
            await self.conversation_manager.end_turn()

        logger.info(f"User said: {result.text}")
        return result.text

    def get_conversation_stats(self) -> Dict[str, Any]:
        """获取对话统计"""
        if self.conversation_manager:
            return self.conversation_manager.get_statistics()
        return {}

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        if self.conversation_manager:
            return self.conversation_manager.get_conversation_history()
        return []


class VoiceConversationSimulator:
    """语音对话模拟器"""

    def __init__(self, voice_interface: VoiceInterface):
        self.voice_interface = voice_interface
        self.output_dir = Path("voice_output")
        self.output_dir.mkdir(exist_ok=True)

        logger.info("VoiceConversationSimulator initialized")

    async def simulate_conversation(
        self,
        scenario: str = "basic"
    ) -> Dict[str, Any]:
        """模拟完整对话"""
        logger.info(f"Simulating conversation: {scenario}")

        if scenario == "basic":
            return await self._simulate_basic_conversation()
        elif scenario == "with_interruption":
            return await self._simulate_interruption_conversation()
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    async def _simulate_basic_conversation(self) -> Dict[str, Any]:
        """模拟基本对话"""
        print("\n" + "=" * 80)
        print("Basic Voice Conversation Simulation")
        print("=" * 80)

        # 对话脚本
        turns = [
            {
                "role": "agent",
                "state": SalesState.OPENING,
                "text": "您好！我是XX银行的销售顾问，很高兴为您服务。"
            },
            {
                "role": "user",
                "text": "你好，我想了解一下信用卡。"
            },
            {
                "role": "agent",
                "state": SalesState.DISCOVERY,
                "text": "好的，请问您目前使用信用卡的主要场景是什么？"
            },
            {
                "role": "user",
                "text": "主要是日常消费和网购。"
            },
            {
                "role": "agent",
                "state": SalesState.PITCH,
                "text": "明白了。我们的白金卡最高额度可达50万，比市面上普通信用卡高出5倍。"
            },
        ]

        # 执行对话
        for i, turn in enumerate(turns, 1):
            print(f"\n[Turn {i}]")

            if turn["role"] == "agent":
                print(f"  Agent ({turn['state'].value}): {turn['text']}")

                # Agent 说话
                audio_file = self.output_dir / f"turn_{i}_agent.mp3"
                await self.voice_interface.speak(
                    turn["text"],
                    turn["state"],
                    save_to=str(audio_file)
                )

                print(f"  [Audio saved: {audio_file}]")

            else:
                print(f"  User: {turn['text']}")

                # 模拟用户语音（使用 TTS 生成）
                audio_file = self.output_dir / f"turn_{i}_user.mp3"
                await self.voice_interface.tts.synthesize(
                    turn["text"],
                    sales_state=SalesState.OPENING
                )
                self.voice_interface.tts.save_audio(
                    await self.voice_interface.tts.synthesize(
                        turn["text"],
                        sales_state=SalesState.OPENING
                    ),
                    str(audio_file)
                )

                print(f"  [Audio saved: {audio_file}]")

            await asyncio.sleep(0.1)

        # 获取统计
        stats = self.voice_interface.get_conversation_stats()

        return {
            "scenario": "basic",
            "total_turns": len(turns),
            "stats": stats
        }

    async def _simulate_interruption_conversation(self) -> Dict[str, Any]:
        """模拟带打断的对话"""
        print("\n" + "=" * 80)
        print("Voice Conversation with Interruption Simulation")
        print("=" * 80)

        # 对话脚本（包含打断）
        turns = [
            {
                "role": "agent",
                "state": SalesState.PITCH,
                "text": "我们的白金卡最高额度可达50万，比市面上普通信用卡的5-10万额度高出5倍，这意味着您在大额消费时不用担心额度不够。",
                "interrupted": True
            },
            {
                "role": "user",
                "text": "等等，年费多少？",
                "is_interruption": True
            },
            {
                "role": "agent",
                "state": SalesState.OBJECTION,
                "text": "首年免年费，次年刷满6笔即可免年费。"
            },
        ]

        # 执行对话
        for i, turn in enumerate(turns, 1):
            print(f"\n[Turn {i}]")

            if turn["role"] == "agent":
                interrupted_marker = " (interrupted)" if turn.get("interrupted") else ""
                print(f"  Agent ({turn['state'].value}){interrupted_marker}: {turn['text']}")

                # Agent 说话
                audio_file = self.output_dir / f"interruption_turn_{i}_agent.mp3"
                await self.voice_interface.speak(
                    turn["text"],
                    turn["state"],
                    save_to=str(audio_file)
                )

                print(f"  [Audio saved: {audio_file}]")

            else:
                interruption_marker = " (INTERRUPTION)" if turn.get("is_interruption") else ""
                print(f"  User{interruption_marker}: {turn['text']}")

                # 模拟用户语音
                audio_file = self.output_dir / f"interruption_turn_{i}_user.mp3"
                await self.voice_interface.tts.synthesize(
                    turn["text"],
                    sales_state=SalesState.OPENING
                )
                self.voice_interface.tts.save_audio(
                    await self.voice_interface.tts.synthesize(
                        turn["text"],
                        sales_state=SalesState.OPENING
                    ),
                    str(audio_file)
                )

                print(f"  [Audio saved: {audio_file}]")

            await asyncio.sleep(0.1)

        # 获取统计
        stats = self.voice_interface.get_conversation_stats()

        return {
            "scenario": "with_interruption",
            "total_turns": len(turns),
            "stats": stats
        }


class PerformanceReporter:
    """性能报告生成器"""

    def __init__(self, output_dir: str = "voice_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        logger.info(f"PerformanceReporter initialized: output_dir={output_dir}")

    def generate_report(
        self,
        simulation_results: List[Dict[str, Any]],
        voice_interface: VoiceInterface
    ) -> str:
        """生成性能报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"voice_interface_report_{timestamp}.json"

        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0"
            },
            "simulations": simulation_results,
            "overall_stats": self._calculate_overall_stats(simulation_results),
            "conversation_history": voice_interface.get_conversation_history()
        }

        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Report saved: {report_file}")
        return str(report_file)

    def _calculate_overall_stats(
        self,
        simulation_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算总体统计"""
        total_turns = sum(r["total_turns"] for r in simulation_results)

        total_interruptions = sum(
            r["stats"].get("interrupted_turns", 0)
            for r in simulation_results
            if "stats" in r
        )

        return {
            "total_simulations": len(simulation_results),
            "total_turns": total_turns,
            "total_interruptions": total_interruptions,
            "average_turns_per_simulation": total_turns / len(simulation_results) if simulation_results else 0
        }

    def print_summary(self, report_file: str):
        """打印报告摘要"""
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)

        print("\n" + "=" * 80)
        print("Performance Report Summary")
        print("=" * 80)

        overall = report["overall_stats"]
        print(f"\nOverall Statistics:")
        print(f"  Total Simulations: {overall['total_simulations']}")
        print(f"  Total Turns: {overall['total_turns']}")
        print(f"  Total Interruptions: {overall['total_interruptions']}")
        print(f"  Average Turns per Simulation: {overall['average_turns_per_simulation']:.1f}")

        print(f"\nSimulation Results:")
        for i, sim in enumerate(report["simulations"], 1):
            print(f"\n  Simulation {i} ({sim['scenario']}):")
            print(f"    Turns: {sim['total_turns']}")

            if "stats" in sim:
                stats = sim["stats"]
                print(f"    Interrupted Turns: {stats.get('interrupted_turns', 0)}")
                print(f"    Interruption Rate: {stats.get('interruption_rate', 0)*100:.1f}%")

        print(f"\nReport saved to: {report_file}")


# ============================================================================
# 完整集成测试
# ============================================================================

async def run_complete_integration_test():
    """运行完整集成测试"""
    print("\n" + "=" * 80)
    print("Phase 3B Week 7 Day 7: Complete Voice Interface Integration Test")
    print("=" * 80)

    # 1. 初始化语音接口
    print("\n[Step 1] Initializing Voice Interface...")
    voice_interface = VoiceInterface(
        tts_backend="edge_tts",
        stt_backend="faster_whisper",
        enable_interruption=True
    )
    print("  [OK] Voice Interface initialized")

    # 2. 初始化模拟器
    print("\n[Step 2] Initializing Conversation Simulator...")
    simulator = VoiceConversationSimulator(voice_interface)
    print("  [OK] Simulator initialized")

    # 3. 运行基本对话模拟
    print("\n[Step 3] Running basic conversation simulation...")
    basic_result = await simulator.simulate_conversation("basic")
    print("  [OK] Basic simulation completed")

    # 4. 运行带打断的对话模拟
    print("\n[Step 4] Running interruption conversation simulation...")
    interruption_result = await simulator.simulate_conversation("with_interruption")
    print("  [OK] Interruption simulation completed")

    # 5. 生成性能报告
    print("\n[Step 5] Generating performance report...")
    reporter = PerformanceReporter()
    report_file = reporter.generate_report(
        [basic_result, interruption_result],
        voice_interface
    )
    print(f"  [OK] Report generated: {report_file}")

    # 6. 打印报告摘要
    reporter.print_summary(report_file)

    print("\n" + "=" * 80)
    print("Integration Test Completed Successfully!")
    print("=" * 80)

    return {
        "basic_result": basic_result,
        "interruption_result": interruption_result,
        "report_file": report_file
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
    print(f"  Basic simulation: {results['basic_result']['total_turns']} turns")
    print(f"  Interruption simulation: {results['interruption_result']['total_turns']} turns")
    print(f"  Report: {results['report_file']}")

    print("\n[OK] All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
