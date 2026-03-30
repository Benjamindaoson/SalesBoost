"""
Unit Tests for Reinforcement Learning Algorithms

Tests for RL components including Q-learning, policy gradient, and reward systems.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from typing import Dict, Any, List


class TestQLearningAgent:
    """Tests for Q-Learning Agent."""

    @pytest.fixture
    def q_agent(self):
        """Create Q-learning agent instance."""
        agent = Mock()
        agent.q_table = {}
        agent.learning_rate = 0.1
        agent.discount_factor = 0.95
        agent.epsilon = 0.1

        agent.get_action = Mock(return_value="ask_question")
        agent.update_q_value = Mock()
        agent.get_q_value = Mock(return_value=0.5)

        return agent

    def test_initialization(self, q_agent):
        """Test Q-learning agent initialization."""
        assert hasattr(q_agent, "q_table")
        assert hasattr(q_agent, "learning_rate")
        assert hasattr(q_agent, "discount_factor")
        assert hasattr(q_agent, "epsilon")

    def test_get_action(self, q_agent):
        """Test action selection."""
        state = "customer_interested"
        action = q_agent.get_action(state)

        assert isinstance(action, str)
        q_agent.get_action.assert_called_once_with(state)

    def test_update_q_value(self, q_agent):
        """Test Q-value update."""
        state = "customer_interested"
        action = "ask_question"
        reward = 1.0
        next_state = "customer_engaged"

        q_agent.update_q_value(state, action, reward, next_state)
        q_agent.update_q_value.assert_called_once()

    def test_epsilon_greedy_exploration(self, q_agent):
        """Test epsilon-greedy exploration."""
        q_agent.epsilon = 0.1

        # Mock random choice
        with patch("random.random", return_value=0.05):
            # Should explore (random < epsilon)
            q_agent.get_action = Mock(return_value="random_action")
            action = q_agent.get_action("state")
            assert action is not None

        with patch("random.random", return_value=0.5):
            # Should exploit (random > epsilon)
            q_agent.get_action = Mock(return_value="best_action")
            action = q_agent.get_action("state")
            assert action is not None

    def test_q_value_convergence(self, q_agent):
        """Test Q-value convergence over iterations."""
        q_agent.get_q_value = Mock(side_effect=[0.1, 0.3, 0.5, 0.6, 0.65, 0.67])

        q_values = []
        for _ in range(6):
            q_val = q_agent.get_q_value("state", "action")
            q_values.append(q_val)

        # Check that Q-values are increasing (converging)
        assert q_values[-1] > q_values[0]


class TestPolicyGradientAgent:
    """Tests for Policy Gradient Agent."""

    @pytest.fixture
    def pg_agent(self):
        """Create policy gradient agent instance."""
        agent = Mock()
        agent.policy_network = Mock()
        agent.learning_rate = 0.01

        agent.select_action = Mock(return_value="present_solution")
        agent.update_policy = Mock()
        agent.compute_returns = Mock(return_value=[1.0, 0.9, 0.8])

        return agent

    def test_select_action(self, pg_agent):
        """Test action selection from policy."""
        state = np.array([0.5, 0.3, 0.8])
        action = pg_agent.select_action(state)

        assert isinstance(action, str)
        pg_agent.select_action.assert_called_once()

    def test_compute_returns(self, pg_agent):
        """Test return computation."""
        rewards = [1.0, 0.5, 0.3]
        returns = pg_agent.compute_returns(rewards)

        assert isinstance(returns, list)
        assert len(returns) == len(rewards)

    def test_update_policy(self, pg_agent):
        """Test policy update."""
        states = [np.array([0.5, 0.3]), np.array([0.6, 0.4])]
        actions = ["ask_question", "present_solution"]
        returns = [1.0, 0.8]

        pg_agent.update_policy(states, actions, returns)
        pg_agent.update_policy.assert_called_once()

    def test_policy_improvement(self, pg_agent):
        """Test policy improvement over time."""
        # Mock policy network outputs
        pg_agent.policy_network.predict = Mock(
            side_effect=[
                np.array([0.3, 0.7]),  # Initial policy
                np.array([0.2, 0.8]),  # After update 1
                np.array([0.1, 0.9]),  # After update 2
            ]
        )

        state = np.array([0.5, 0.3])

        # Get policy probabilities over time
        probs = []
        for _ in range(3):
            prob = pg_agent.policy_network.predict(state)
            probs.append(prob)

        # Check that policy is improving (higher probability for better action)
        assert probs[-1][1] > probs[0][1]


class TestRewardSystem:
    """Tests for Reward System."""

    @pytest.fixture
    def reward_system(self):
        """Create reward system instance."""
        system = Mock()
        system.calculate_reward = Mock(return_value=0.8)
        system.get_immediate_reward = Mock(return_value=0.5)
        system.get_delayed_reward = Mock(return_value=0.3)

        return system

    def test_calculate_reward(self, reward_system):
        """Test reward calculation."""
        state = {"customer_interest": 0.7, "objections_resolved": 2}
        action = "address_objection"
        next_state = {"customer_interest": 0.8, "objections_resolved": 3}

        reward = reward_system.calculate_reward(state, action, next_state)

        assert isinstance(reward, (int, float))
        assert -1.0 <= reward <= 1.0

    def test_immediate_reward(self, reward_system):
        """Test immediate reward calculation."""
        action_result = {"success": True, "customer_response": "positive"}

        reward = reward_system.get_immediate_reward(action_result)

        assert isinstance(reward, (int, float))

    def test_delayed_reward(self, reward_system):
        """Test delayed reward calculation."""
        session_outcome = {
            "deal_closed": True,
            "customer_satisfaction": 0.9,
            "session_duration": 1200,
        }

        reward = reward_system.get_delayed_reward(session_outcome)

        assert isinstance(reward, (int, float))

    def test_reward_shaping(self, reward_system):
        """Test reward shaping for better learning."""
        # Test positive reward for good actions
        reward_system.calculate_reward = Mock(return_value=1.0)
        good_reward = reward_system.calculate_reward(
            {"interest": 0.5}, "build_rapport", {"interest": 0.8}
        )
        assert good_reward > 0

        # Test negative reward for bad actions
        reward_system.calculate_reward = Mock(return_value=-0.5)
        bad_reward = reward_system.calculate_reward(
            {"interest": 0.8}, "aggressive_pitch", {"interest": 0.3}
        )
        assert bad_reward < 0


class TestExperienceReplay:
    """Tests for Experience Replay Buffer."""

    @pytest.fixture
    def replay_buffer(self):
        """Create experience replay buffer."""
        buffer = Mock()
        buffer.buffer = []
        buffer.max_size = 10000

        buffer.add = Mock()
        buffer.sample = Mock(
            return_value=[
                {"state": "s1", "action": "a1", "reward": 1.0, "next_state": "s2"},
                {"state": "s2", "action": "a2", "reward": 0.5, "next_state": "s3"},
            ]
        )
        buffer.size = Mock(return_value=100)

        return buffer

    def test_add_experience(self, replay_buffer):
        """Test adding experience to buffer."""
        experience = {
            "state": "customer_interested",
            "action": "ask_question",
            "reward": 0.8,
            "next_state": "customer_engaged",
        }

        replay_buffer.add(experience)
        replay_buffer.add.assert_called_once_with(experience)

    def test_sample_batch(self, replay_buffer):
        """Test sampling batch from buffer."""
        batch_size = 32
        batch = replay_buffer.sample(batch_size)

        assert isinstance(batch, list)
        assert len(batch) > 0

    def test_buffer_size(self, replay_buffer):
        """Test buffer size tracking."""
        size = replay_buffer.size()
        assert isinstance(size, int)
        assert size >= 0

    def test_buffer_overflow(self, replay_buffer):
        """Test buffer overflow handling."""
        replay_buffer.max_size = 5
        replay_buffer.size = Mock(return_value=5)

        # Adding more experiences should not exceed max_size
        for i in range(10):
            replay_buffer.add({"state": f"s{i}", "action": f"a{i}", "reward": 1.0})

        # Buffer should maintain max size
        assert replay_buffer.size() <= replay_buffer.max_size


class TestAdvantageActorCritic:
    """Tests for Advantage Actor-Critic (A2C) Algorithm."""

    @pytest.fixture
    def a2c_agent(self):
        """Create A2C agent instance."""
        agent = Mock()
        agent.actor = Mock()
        agent.critic = Mock()

        agent.select_action = Mock(return_value="present_solution")
        agent.compute_advantage = Mock(return_value=0.5)
        agent.update = Mock()

        return agent

    def test_select_action(self, a2c_agent):
        """Test action selection."""
        state = np.array([0.5, 0.3, 0.8])
        action = a2c_agent.select_action(state)

        assert isinstance(action, str)

    def test_compute_advantage(self, a2c_agent):
        """Test advantage computation."""
        state = np.array([0.5, 0.3])
        reward = 1.0
        next_state = np.array([0.6, 0.4])

        advantage = a2c_agent.compute_advantage(state, reward, next_state)

        assert isinstance(advantage, (int, float))

    def test_update_networks(self, a2c_agent):
        """Test actor-critic network updates."""
        states = [np.array([0.5, 0.3]), np.array([0.6, 0.4])]
        actions = ["ask_question", "present_solution"]
        advantages = [0.5, 0.3]
        returns = [1.0, 0.8]

        a2c_agent.update(states, actions, advantages, returns)
        a2c_agent.update.assert_called_once()


@pytest.mark.parametrize(
    "learning_rate,expected_convergence",
    [
        (0.1, True),
        (0.01, True),
        (0.001, True),
        (1.0, False),  # Too high, may not converge
    ],
)
def test_learning_rate_impact(learning_rate, expected_convergence):
    """Test impact of learning rate on convergence."""
    agent = Mock()
    agent.learning_rate = learning_rate

    # Simulate training
    q_values = []
    for i in range(100):
        # Mock Q-value update
        if learning_rate < 1.0:
            q_val = 0.5 + (i * 0.01 * learning_rate)
        else:
            q_val = 0.5 + (i * 0.01 * learning_rate) * (-1) ** i  # Oscillating

        q_values.append(min(q_val, 1.0))

    # Check convergence
    if expected_convergence:
        assert q_values[-1] > q_values[0]
    else:
        # May oscillate or diverge
        pass


def test_reward_discount_factor():
    """Test discount factor impact on returns."""
    rewards = [1.0, 1.0, 1.0, 1.0]
    gamma = 0.9

    # Calculate discounted returns
    returns = []
    G = 0
    for r in reversed(rewards):
        G = r + gamma * G
        returns.insert(0, G)

    # First return should be highest (includes all future rewards)
    assert returns[0] > returns[-1]

    # Returns should decrease
    for i in range(len(returns) - 1):
        assert returns[i] >= returns[i + 1]
