"""Sales Agent - specialized agent for sales conversations.

This agent handles:
- Sales reasoning and strategy
- Response generation
- Customer interaction
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from salesagent.agent.base_agent import AgentCapability, BaseAgent, Message

if TYPE_CHECKING:
    from salesagent.llm.gateway import ModelGateway

log = structlog.get_logger()


class SalesAgent(BaseAgent):
    """Sales Agent for handling sales conversations.

    This agent combines:
    - Reasoning (from reasoning_node)
    - Strategy planning (from strategy_node)
    - Response generation (from response_node)

    Capabilities:
    - REASONING: Analyze customer intent and needs
    - STRATEGY_PLANNING: Plan sales tactics
    - RESPONSE_GENERATION: Generate sales responses
    """

    def __init__(
        self,
        name: str = "sales_agent",
        gateway: ModelGateway = None,
    ):
        super().__init__(
            name=name,
            role="Sales conversation specialist",
            capabilities=[
                AgentCapability.REASONING,
                AgentCapability.STRATEGY_PLANNING,
                AgentCapability.RESPONSE_GENERATION,
            ],
        )
        self.gateway = gateway

    async def process(self, message: Message) -> dict[str, Any]:
        """Process a sales-related message.

        Args:
            message: Message containing user input and context

        Returns:
            Dictionary with sales response and reasoning
        """
        content = message.content
        task = content.get("task", "generate_response")

        log.info(
            "SalesAgent processing",
            agent_name=self.name,
            task=task,
            message_id=message.message_id,
        )

        if task == "reasoning":
            return await self._do_reasoning(content)
        elif task == "strategy":
            return await self._do_strategy(content)
        elif task == "generate_response":
            return await self._generate_response(content)
        else:
            raise ValueError(f"Unknown task: {task}")

    async def _do_reasoning(self, content: dict[str, Any]) -> dict[str, Any]:
        """Perform sales reasoning.

        Analyzes customer message to extract:
        - Literal intent
        - Hidden needs
        - Emotional state
        - Stage signal
        - Primary tactic
        - Confidence
        """
        # Import here to avoid circular dependency
        from salesagent.orchestration.nodes.reasoning import reasoning_node

        # Create minimal state for reasoning
        state = {
            "session_id": content.get("session_id"),
            "user_message": content.get("user_message"),
            "messages": content.get("messages", []),
            "fsm_stage": content.get("fsm_stage"),
            "customer_profile": content.get("customer_profile", {}),
        }

        # Call reasoning node
        result = await reasoning_node(state, self.gateway, redis=None)

        return {
            "reasoning_output": result.get("reasoning_output"),
        }

    async def _do_strategy(self, content: dict[str, Any]) -> dict[str, Any]:
        """Plan sales strategy.

        Based on reasoning output, plan:
        - Tactics to use
        - Key points to emphasize
        - Objections to address
        """
        # Import here to avoid circular dependency
        from salesagent.orchestration.nodes.strategy import strategy_node

        state = {
            "session_id": content.get("session_id"),
            "reasoning_output": content.get("reasoning_output"),
            "customer_profile": content.get("customer_profile", {}),
            "fsm_stage": content.get("fsm_stage"),
        }

        result = await strategy_node(state, self.gateway)

        return {
            "strategy_output": result.get("strategy_output"),
        }

    async def _generate_response(self, content: dict[str, Any]) -> dict[str, Any]:
        """Generate sales response.

        Based on reasoning and strategy, generate appropriate response.
        """
        # Import here to avoid circular dependency
        from salesagent.orchestration.nodes.response import response_node

        state = {
            "session_id": content.get("session_id"),
            "messages": content.get("messages", []),
            "reasoning_output": content.get("reasoning_output"),
            "strategy_output": content.get("strategy_output"),
            "retrieved_docs": content.get("retrieved_docs", []),
            "fsm_stage": content.get("fsm_stage"),
            "guard_active": content.get("guard_active", True),
        }

        # Get guard from content if provided
        guard = content.get("guard")

        result = await response_node(state, self.gateway, guard=guard)

        return {
            "response_text": result.get("response_text"),
            "guard_events": result.get("guard_events", []),
        }


class AnalystAgent(BaseAgent):
    """Analyst Agent for customer analysis.

    This agent handles:
    - Customer profile extraction
    - Sentiment analysis
    - Needs identification

    Capabilities:
    - ANALYSIS: Analyze customer data
    """

    def __init__(
        self,
        name: str = "analyst_agent",
        gateway: ModelGateway = None,
    ):
        super().__init__(
            name=name,
            role="Customer analysis specialist",
            capabilities=[AgentCapability.ANALYSIS],
        )
        self.gateway = gateway

    async def process(self, message: Message) -> dict[str, Any]:
        """Process an analysis request.

        Args:
            message: Message containing customer data to analyze

        Returns:
            Dictionary with analysis results
        """
        content = message.content

        log.info(
            "AnalystAgent processing",
            agent_name=self.name,
            message_id=message.message_id,
        )

        # Import here to avoid circular dependency
        from salesagent.orchestration.nodes.analyzer import analyzer_node

        state = {
            "session_id": content.get("session_id"),
            "user_message": content.get("user_message"),
            "messages": content.get("messages", []),
            "customer_profile": content.get("customer_profile", {}),
            "reasoning_output": content.get("reasoning_output"),
        }

        result = await analyzer_node(state, self.gateway)

        return {
            "customer_profile": result.get("customer_profile"),
        }


class GuardAgent(BaseAgent):
    """Guard Agent for compliance checking.

    This agent handles:
    - Real-time compliance checks
    - Risk detection
    - Content filtering

    Capabilities:
    - COMPLIANCE_CHECK: Check for compliance violations
    """

    def __init__(
        self,
        name: str = "guard_agent",
        guard=None,
    ):
        super().__init__(
            name=name,
            role="Compliance and safety specialist",
            capabilities=[AgentCapability.COMPLIANCE_CHECK],
        )
        self.guard = guard

    async def process(self, message: Message) -> dict[str, Any]:
        """Process a compliance check request.

        Args:
            message: Message containing text to check

        Returns:
            Dictionary with compliance check results
        """
        content = message.content
        text = content.get("text", "")

        log.info(
            "GuardAgent processing",
            agent_name=self.name,
            message_id=message.message_id,
            text_length=len(text),
        )

        if not self.guard:
            return {"compliant": True, "risk_events": []}

        # Check for compliance violations
        risk_events = []
        sentences = text.split("。")  # Split by Chinese period

        for sentence in sentences:
            if not sentence.strip():
                continue

            risk_type = self.guard.check_sentence(sentence)
            if risk_type:
                risk_events.append({
                    "sentence": sentence,
                    "risk_type": risk_type.value,
                })

        return {
            "compliant": len(risk_events) == 0,
            "risk_events": risk_events,
        }


class RetrievalAgent(BaseAgent):
    """Retrieval Agent for knowledge base queries.

    This agent handles:
    - Document retrieval
    - Semantic search
    - Context gathering

    Capabilities:
    - RETRIEVAL: Retrieve relevant documents
    """

    def __init__(
        self,
        name: str = "retrieval_agent",
        gateway: ModelGateway = None,
        db=None,
    ):
        super().__init__(
            name=name,
            role="Knowledge retrieval specialist",
            capabilities=[AgentCapability.RETRIEVAL],
        )
        self.gateway = gateway
        self.db = db

    async def process(self, message: Message) -> dict[str, Any]:
        """Process a retrieval request.

        Args:
            message: Message containing query

        Returns:
            Dictionary with retrieved documents
        """
        content = message.content

        log.info(
            "RetrievalAgent processing",
            agent_name=self.name,
            message_id=message.message_id,
        )

        # Import here to avoid circular dependency
        from salesagent.orchestration.nodes.retrieval import retrieval_node

        state = {
            "session_id": content.get("session_id"),
            "user_message": content.get("user_message"),
            "reasoning_output": content.get("reasoning_output"),
        }

        result = await retrieval_node(state, self.gateway, self.db)

        return {
            "retrieved_docs": result.get("retrieved_docs", []),
        }
