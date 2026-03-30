"""
Mixture of Experts (MoE) Router - 动态专家路由系统

2026年前沿算法：MoE with Dynamic Routing

核心思想：
1. 多个专家模型（Expert Models）
2. 门控网络（Gating Network）动态路由
3. 稀疏激活（只激活top-k专家）
4. 负载均衡
5. 在线学习优化

Author: Claude (Anthropic)
Version: 2026.1
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class ExpertModel:
    """
    专家模型

    每个专家专注于特定类型的销售任务
    """

    def __init__(
        self,
        expert_name: str,
        specialization: str,
        llm_client=None,
    ):
        """
        Initialize expert model

        Args:
            expert_name: Expert identifier
            specialization: What this expert specializes in
            llm_client: LLM client for generation
        """
        self.expert_name = expert_name
        self.specialization = specialization
        self.llm_client = llm_client

        # Performance tracking
        self.total_calls = 0
        self.total_success = 0
        self.avg_latency = 0.0

        logger.info(f"ExpertModel initialized: {expert_name} ({specialization})")

    async def generate(
        self,
        context: Dict[str, Any],
        query: str,
    ) -> str:
        """
        Generate response using this expert

        Args:
            context: Conversation context
            query: User query

        Returns:
            Expert's response
        """
        self.total_calls += 1

        # Build expert-specific prompt
        system_prompt = self._build_expert_prompt()

        user_prompt = f"""Context: {context}

Query: {query}

Generate a response using your expertise in {self.specialization}."""

        try:
            if self.llm_client:
                result = await self.llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                )
                response = result.content
            else:
                # Mock response for demo
                response = self._generate_mock_response(query)

            self.total_success += 1
            return response

        except Exception as e:
            logger.error(f"Expert {self.expert_name} generation failed: {e}")
            return f"[Expert {self.expert_name} error]"

    def _build_expert_prompt(self) -> str:
        """Build expert-specific system prompt"""
        prompts = {
            "discovery": """You are a SPIN questioning expert. Your specialty is asking insightful discovery questions to uncover customer needs.

Focus on:
- Situation questions
- Problem questions
- Implication questions
- Need-payoff questions

Be curious, empathetic, and strategic.""",

            "objection": """You are an objection handling expert. Your specialty is addressing customer concerns empathetically and effectively.

Focus on:
- Acknowledging concerns
- Clarifying the real issue
- Providing evidence
- Reframing objections

Be understanding, patient, and solution-oriented.""",

            "closing": """You are a closing expert. Your specialty is recognizing buying signals and moving deals forward.

Focus on:
- Identifying readiness
- Creating urgency (ethically)
- Proposing next steps
- Asking for commitment

Be confident, clear, and action-oriented.""",

            "rapport": """You are a rapport-building expert. Your specialty is creating genuine connections with customers.

Focus on:
- Finding common ground
- Active listening
- Showing genuine interest
- Building trust

Be warm, authentic, and personable.""",

            "technical": """You are a technical expert. Your specialty is explaining complex product features clearly.

Focus on:
- Simplifying technical concepts
- Using analogies
- Demonstrating value
- Answering technical questions

Be clear, accurate, and educational.""",

            "pricing": """You are a pricing negotiation expert. Your specialty is discussing pricing and value.

Focus on:
- Framing value vs. cost
- Handling price objections
- Offering options
- Justifying pricing

Be confident, value-focused, and flexible.""",
        }

        return prompts.get(
            self.specialization,
            "You are a sales expert. Provide helpful, professional responses."
        )

    def _generate_mock_response(self, query: str) -> str:
        """Generate mock response for demo"""
        mock_responses = {
            "discovery": "That's interesting! Can you tell me more about how you currently handle that process?",
            "objection": "I completely understand your concern. Many of our clients had similar questions initially. Let me address that...",
            "closing": "Based on what we've discussed, it sounds like this could be a great fit. Would you like to move forward with a pilot?",
            "rapport": "I really appreciate you taking the time to chat with me today. How has your week been going?",
            "technical": "Let me break that down for you. Essentially, the system works by...",
            "pricing": "I understand budget is important. Let's look at the ROI you'd get from this investment...",
        }

        return mock_responses.get(
            self.specialization,
            "Let me help you with that."
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get expert statistics"""
        return {
            "expert_name": self.expert_name,
            "specialization": self.specialization,
            "total_calls": self.total_calls,
            "success_rate": self.total_success / max(self.total_calls, 1),
            "avg_latency": self.avg_latency,
        }


class GatingNetwork(nn.Module):
    """
    门控网络：学习如何路由到专家

    使用神经网络学习最优路由策略
    """

    def __init__(
        self,
        input_dim: int,
        num_experts: int,
        hidden_dim: int = 256,
        top_k: int = 2,
    ):
        """
        Initialize gating network

        Args:
            input_dim: Context embedding dimension
            num_experts: Number of expert models
            hidden_dim: Hidden layer dimension
            top_k: Number of experts to activate
        """
        super().__init__()

        self.input_dim = input_dim
        self.num_experts = num_experts
        self.top_k = top_k

        # Network layers
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, num_experts)

        # Batch normalization
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim // 2)

        # Dropout for regularization
        self.dropout = nn.Dropout(0.1)

        logger.info(f"GatingNetwork initialized: {num_experts} experts, top-{top_k}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass

        Args:
            x: Context embedding [batch_size, input_dim]

        Returns:
            Expert weights [batch_size, num_experts]
        """
        # Layer 1
        x = self.fc1(x)
        if x.shape[0] > 1:  # Only use BN if batch size > 1
            x = self.bn1(x)
        x = F.relu(x)
        x = self.dropout(x)

        # Layer 2
        x = self.fc2(x)
        if x.shape[0] > 1:
            x = self.bn2(x)
        x = F.relu(x)
        x = self.dropout(x)

        # Output layer
        logits = self.fc3(x)

        # Add noise for exploration (during training)
        if self.training:
            noise = torch.randn_like(logits) * 0.1
            logits = logits + noise

        # Softmax to get probabilities
        weights = F.softmax(logits, dim=-1)

        return weights

    def select_top_k(self, weights: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Select top-k experts

        Args:
            weights: Expert weights [batch_size, num_experts]

        Returns:
            (top_k_indices, top_k_weights)
        """
        top_k_weights, top_k_indices = torch.topk(weights, k=self.top_k, dim=-1)

        # Renormalize
        top_k_weights = F.softmax(top_k_weights, dim=-1)

        return top_k_indices, top_k_weights


class MixtureOfExpertsRouter:
    """
    MoE动态路由系统

    核心功能：
    1. 维护多个专家模型
    2. 使用门控网络动态路由
    3. 稀疏激活（top-k）
    4. 负载均衡
    5. 在线学习优化

    Usage:
        router = MixtureOfExpertsRouter(
            experts=["discovery", "objection", "closing"],
            llm_client=llm
        )

        response = await router.route_and_generate(
            context={"stage": "discovery"},
            query="What are your current challenges?"
        )
    """

    def __init__(
        self,
        expert_specs: List[Tuple[str, str]],  # [(name, specialization), ...]
        llm_client=None,
        context_dim: int = 768,
        top_k: int = 2,
        learning_rate: float = 0.001,
    ):
        """
        Initialize MoE router

        Args:
            expert_specs: List of (expert_name, specialization) tuples
            llm_client: LLM client for experts
            context_dim: Context embedding dimension
            top_k: Number of experts to activate
            learning_rate: Learning rate for gating network
        """
        self.llm_client = llm_client
        self.context_dim = context_dim
        self.top_k = top_k

        # Initialize experts
        self.experts = {
            name: ExpertModel(name, spec, llm_client)
            for name, spec in expert_specs
        }

        # Initialize gating network
        self.gating_network = GatingNetwork(
            input_dim=context_dim,
            num_experts=len(self.experts),
            hidden_dim=256,
            top_k=top_k,
        )

        # Optimizer for online learning
        self.optimizer = torch.optim.Adam(
            self.gating_network.parameters(),
            lr=learning_rate
        )

        # Expert name to index mapping
        self.expert_names = list(self.experts.keys())

        # Statistics
        self.total_routes = 0
        self.expert_usage = {name: 0 for name in self.expert_names}

        logger.info(f"MixtureOfExpertsRouter initialized with {len(self.experts)} experts")

    async def route_and_generate(
        self,
        context: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        """
        Route to experts and generate response

        Steps:
        1. Encode context
        2. Gating network computes expert weights
        3. Select top-k experts
        4. Parallel expert calls
        5. Weighted fusion of outputs

        Args:
            context: Conversation context
            query: User query

        Returns:
            Dict with response, selected_experts, weights
        """
        self.total_routes += 1

        # 1. Encode context
        context_embedding = self._encode_context(context, query)

        # 2. Gating network
        with torch.no_grad():
            expert_weights = self.gating_network(context_embedding)

        # 3. Select top-k experts
        top_k_indices, top_k_weights = self.gating_network.select_top_k(expert_weights)

        # Convert to expert names
        selected_experts = [
            self.expert_names[idx.item()]
            for idx in top_k_indices[0]
        ]

        # Update usage statistics
        for expert_name in selected_experts:
            self.expert_usage[expert_name] += 1

        logger.info(f"Selected experts: {selected_experts} with weights {top_k_weights[0].tolist()}")

        # 4. Parallel expert calls
        expert_outputs = await asyncio.gather(*[
            self.experts[name].generate(context, query)
            for name in selected_experts
        ])

        # 5. Weighted fusion
        final_output = self._fuse_outputs(
            expert_outputs,
            top_k_weights[0]
        )

        return {
            "response": final_output,
            "selected_experts": selected_experts,
            "expert_weights": top_k_weights[0].tolist(),
            "all_expert_weights": expert_weights[0].tolist(),
        }

    def _encode_context(
        self,
        context: Dict[str, Any],
        query: str
    ) -> torch.Tensor:
        """
        Encode context into embedding

        In production, use a real embedding model (e.g., BGE-M3)
        Here we use a simple feature extraction
        """
        # Extract features
        features = []

        # Stage encoding (one-hot)
        stages = ["opening", "discovery", "presentation", "objection_handling", "closing"]
        current_stage = context.get("stage", "discovery")
        stage_vector = [1.0 if s == current_stage else 0.0 for s in stages]
        features.extend(stage_vector)

        # Numerical features
        features.append(context.get("trust", 0.5))
        features.append(context.get("interest", 0.5))
        features.append(context.get("turn_number", 0) / 20.0)

        # Query features
        query_lower = query.lower()
        features.append(1.0 if "?" in query else 0.0)  # Is question
        features.append(1.0 if any(w in query_lower for w in ["price", "cost", "expensive"]) else 0.0)
        features.append(1.0 if any(w in query_lower for w in ["concern", "worried", "not sure"]) else 0.0)

        # Pad to context_dim
        while len(features) < self.context_dim:
            features.append(0.0)

        features = features[:self.context_dim]

        # Convert to tensor
        embedding = torch.FloatTensor(features).unsqueeze(0)  # [1, context_dim]

        return embedding

    def _fuse_outputs(
        self,
        outputs: List[str],
        weights: torch.Tensor
    ) -> str:
        """
        Fuse multiple expert outputs

        Methods:
        1. Weighted selection (simple)
        2. Token-level fusion (advanced)
        3. Ensemble voting (advanced)

        For now, use weighted selection
        """
        # Simple: select highest weight expert's output
        best_idx = torch.argmax(weights).item()
        return outputs[best_idx]

        # TODO: Implement token-level fusion for production

    async def update_gating_network(
        self,
        context_embedding: torch.Tensor,
        selected_experts: List[str],
        feedback_score: float,
    ):
        """
        Update gating network based on feedback

        Online learning to improve routing

        Args:
            context_embedding: Context that was routed
            selected_experts: Experts that were selected
            feedback_score: Quality score (0.0-1.0)
        """
        # Convert expert names to indices
        expert_indices = [
            self.expert_names.index(name)
            for name in selected_experts
        ]

        # Forward pass
        self.gating_network.train()
        expert_weights = self.gating_network(context_embedding)

        # Calculate loss
        # Reward: increase probability of selected experts if feedback is good
        target = torch.zeros_like(expert_weights)
        for idx in expert_indices:
            target[0, idx] = feedback_score / len(expert_indices)

        loss = F.mse_loss(expert_weights, target)

        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        self.gating_network.eval()

        logger.debug(f"Updated gating network: loss={loss.item():.4f}")

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "total_routes": self.total_routes,
            "expert_usage": self.expert_usage,
            "expert_usage_percentage": {
                name: count / max(self.total_routes, 1) * 100
                for name, count in self.expert_usage.items()
            },
            "experts": {
                name: expert.get_stats()
                for name, expert in self.experts.items()
            },
        }

    def save(self, filepath: str):
        """Save gating network"""
        torch.save({
            "gating_network": self.gating_network.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "expert_names": self.expert_names,
            "stats": self.get_stats(),
        }, filepath)

        logger.info(f"MoE router saved to {filepath}")

    def load(self, filepath: str):
        """Load gating network"""
        checkpoint = torch.load(filepath)

        self.gating_network.load_state_dict(checkpoint["gating_network"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])

        logger.info(f"MoE router loaded from {filepath}")
