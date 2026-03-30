"""
Reinforcement Learning for Agents

[EXPERIMENTAL - NOT PRODUCTION READY]
当前 PPO 实现为 numpy 原型，update() 不更新权重，仅作数学演示。
生产环境请使用 LLM-as-Judge 或 trl/OpenRLHF。

提供强化学习能力：
- PPO策略 (Proximal Policy Optimization)
- 奖励模型 (Reward Model)
- 策略网络 (Policy Network)
"""
import logging

_logger = logging.getLogger(__name__)
_logger.warning(
    "agents.rl is EXPERIMENTAL: PPO update does not apply gradients. "
    "Use LLM-as-Judge or trl for production."
)

from .ppo_policy import PPOPolicy, PolicyNetwork, TacticScorer, TrainablePolicy
from .reward_model import RewardModel, RewardSignal

__all__ = ["PPOPolicy", "PolicyNetwork", "TacticScorer", "TrainablePolicy", "RewardModel", "RewardSignal"]
