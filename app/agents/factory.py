"""
Agent Factory with Dependency Injection

This module provides a factory pattern for creating agents with proper
dependency injection, making the system more testable and maintainable.

Benefits:
- Loose coupling between coordinators and agents
- Easy to mock agents for testing
- Centralized agent configuration
- Support for different agent implementations

Architecture:
    AgentFactory → AgentRegistry → Agent Instances
                 ↓
           Dependency Injection

Usage:
    from app.agents.factory import AgentFactory, AgentType

    factory = AgentFactory()
    coach = factory.create(AgentType.COACH, model_gateway=gateway)
"""

import logging
from typing import Dict, Any, Optional, Protocol, Type
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==================== Agent Protocols ====================

class Agent(Protocol):
    """Base protocol for all agents"""

    async def execute(self, *args, **kwargs) -> Any:
        """Execute agent logic"""
        ...


class CoachAgent(Protocol):
    """Coach agent protocol"""

    async def get_advice(
        self,
        history: list,
        session_id: str,
        turn_number: int
    ) -> Any:
        """Get coaching advice"""
        ...


class NPCAgent(Protocol):
    """NPC agent protocol"""

    async def generate_response(
        self,
        message: str,
        history: list,
        persona: dict,
        stage: str
    ) -> Any:
        """Generate NPC response"""
        ...


class IntentClassifier(Protocol):
    """Intent classifier protocol"""

    async def classify_with_context(
        self,
        message: str,
        history: list,
        fsm_state: dict
    ) -> Any:
        """Classify intent with context"""
        ...


# ==================== Agent Types ====================

class AgentType(str, Enum):
    """Available agent types"""
    COACH = "coach"
    NPC = "npc"
    INTENT = "intent"
    COMPLIANCE = "compliance"
    STRATEGY_ANALYZER = "strategy_analyzer"
    REPORT_GENERATOR = "report_generator"
    SDR = "sdr"


# ==================== Agent Configuration ====================

@dataclass
class AgentConfig:
    """Agent configuration"""
    agent_class: Type
    dependencies: list[str]  # Required dependency names
    singleton: bool = True  # Whether to reuse instance
    config: Dict[str, Any] = None  # Additional config


# ==================== Agent Registry ====================

class AgentRegistry:
    """
    Registry of available agents

    Maintains mapping of agent types to their implementations.
    """

    def __init__(self):
        self._registry: Dict[AgentType, AgentConfig] = {}
        self._instances: Dict[AgentType, Any] = {}

        # Register default agents
        self._register_default_agents()

    def _register_default_agents(self):
        """Register default agent implementations"""
        # Lazy imports to avoid circular dependencies
        from app.agents.ask.coach_agent import SalesCoachAgent
        from app.agents.practice.npc_simulator import NPCGenerator
        from app.engine.intent.context_aware_classifier import ContextAwareIntentClassifier
        from app.agents.roles.compliance_agent import ComplianceAgent
        from app.agents.evaluate.strategy_analyzer import StrategyAnalyzer
        from app.agents.evaluate.report_generator import ReportGenerator

        self.register(
            AgentType.COACH,
            AgentConfig(
                agent_class=SalesCoachAgent,
                dependencies=[],
                singleton=True,
            )
        )

        self.register(
            AgentType.NPC,
            AgentConfig(
                agent_class=NPCGenerator,
                dependencies=["model_gateway"],
                singleton=True,
            )
        )

        self.register(
            AgentType.INTENT,
            AgentConfig(
                agent_class=ContextAwareIntentClassifier,
                dependencies=[],
                singleton=True,
            )
        )

        self.register(
            AgentType.COMPLIANCE,
            AgentConfig(
                agent_class=ComplianceAgent,
                dependencies=[],
                singleton=True,
            )
        )

        self.register(
            AgentType.STRATEGY_ANALYZER,
            AgentConfig(
                agent_class=StrategyAnalyzer,
                dependencies=["model_gateway"],
                singleton=True,
            )
        )

        self.register(
            AgentType.REPORT_GENERATOR,
            AgentConfig(
                agent_class=ReportGenerator,
                dependencies=["model_gateway"],
                singleton=True,
            )
        )

        logger.info(f"[AgentRegistry] Registered {len(self._registry)} agent types")

    def register(self, agent_type: AgentType, config: AgentConfig):
        """Register an agent type"""
        self._registry[agent_type] = config
        logger.debug(f"[AgentRegistry] Registered: {agent_type.value}")

    def get_config(self, agent_type: AgentType) -> Optional[AgentConfig]:
        """Get agent configuration"""
        return self._registry.get(agent_type)

    def list_agents(self) -> list[AgentType]:
        """List all registered agent types"""
        return list(self._registry.keys())


# ==================== Agent Factory ====================

class AgentFactory:
    """
    Factory for creating agents with dependency injection

    Features:
    - Automatic dependency resolution
    - Singleton support
    - Configuration management
    - Easy testing (can inject mocks)
    """

    def __init__(self, registry: Optional[AgentRegistry] = None):
        """
        Initialize agent factory

        Args:
            registry: Agent registry (creates default if None)
        """
        self.registry = registry or AgentRegistry()
        self._dependencies: Dict[str, Any] = {}

    def register_dependency(self, name: str, instance: Any):
        """
        Register a dependency for injection

        Args:
            name: Dependency name (e.g., "model_gateway")
            instance: Dependency instance
        """
        self._dependencies[name] = instance
        logger.debug(f"[AgentFactory] Registered dependency: {name}")

    def create(
        self,
        agent_type: AgentType,
        **kwargs
    ) -> Any:
        """
        Create agent instance

        Args:
            agent_type: Type of agent to create
            **kwargs: Additional arguments (override dependencies)

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type not registered
            RuntimeError: If required dependencies missing
        """
        # Get configuration
        config = self.registry.get_config(agent_type)

        if config is None:
            raise ValueError(f"Agent type not registered: {agent_type.value}")

        # Check if singleton and already created
        if config.singleton and agent_type in self.registry._instances:
            logger.debug(f"[AgentFactory] Reusing singleton: {agent_type.value}")
            return self.registry._instances[agent_type]

        # Resolve dependencies
        resolved_deps = {}

        for dep_name in config.dependencies:
            # Check if provided in kwargs
            if dep_name in kwargs:
                resolved_deps[dep_name] = kwargs[dep_name]
            # Check if registered
            elif dep_name in self._dependencies:
                resolved_deps[dep_name] = self._dependencies[dep_name]
            else:
                raise RuntimeError(
                    f"Missing dependency '{dep_name}' for agent '{agent_type.value}'"
                )

        # Merge with additional config
        if config.config:
            resolved_deps.update(config.config)

        # Merge with kwargs (kwargs override everything)
        resolved_deps.update(kwargs)

        # Create instance
        logger.info(f"[AgentFactory] Creating agent: {agent_type.value}")

        try:
            instance = config.agent_class(**resolved_deps)

            # Store singleton
            if config.singleton:
                self.registry._instances[agent_type] = instance

            return instance

        except Exception as e:
            logger.error(
                f"[AgentFactory] Failed to create agent {agent_type.value}: {e}"
            )
            raise

    def create_all(self, agent_types: list[AgentType], **kwargs) -> Dict[AgentType, Any]:
        """
        Create multiple agents

        Args:
            agent_types: List of agent types to create
            **kwargs: Shared dependencies

        Returns:
            Dict mapping agent types to instances
        """
        agents = {}

        for agent_type in agent_types:
            try:
                agents[agent_type] = self.create(agent_type, **kwargs)
            except Exception as e:
                logger.error(f"[AgentFactory] Failed to create {agent_type.value}: {e}")
                # Continue creating other agents

        return agents

    def clear_singletons(self):
        """Clear all singleton instances (useful for testing)"""
        self.registry._instances.clear()
        logger.info("[AgentFactory] Cleared all singletons")


# ==================== Convenience Functions ====================

_default_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """
    Get default agent factory (singleton)

    Returns:
        AgentFactory instance
    """
    global _default_factory

    if _default_factory is None:
        _default_factory = AgentFactory()

    return _default_factory


def create_agent(agent_type: AgentType, **kwargs) -> Any:
    """
    Convenience function to create agent

    Args:
        agent_type: Agent type
        **kwargs: Dependencies and config

    Returns:
        Agent instance
    """
    factory = get_agent_factory()
    return factory.create(agent_type, **kwargs)


# ==================== Integration with Coordinators ====================

def setup_coordinator_agents(
    model_gateway: Any,
    budget_manager: Any,
    persona: Any,
) -> Dict[str, Any]:
    """
    Setup all agents needed for coordinator

    Args:
        model_gateway: Model gateway instance
        budget_manager: Budget manager instance
        persona: Persona configuration

    Returns:
        Dict of agent instances
    """
    factory = get_agent_factory()

    # Register dependencies
    factory.register_dependency("model_gateway", model_gateway)
    factory.register_dependency("budget_manager", budget_manager)
    factory.register_dependency("persona", persona)

    # Create agents
    agents = factory.create_all([
        AgentType.INTENT,
        AgentType.NPC,
        AgentType.COACH,
        AgentType.COMPLIANCE,
    ])

    return {
        "intent_classifier": agents[AgentType.INTENT],
        "npc_agent": agents[AgentType.NPC],
        "coach_agent": agents[AgentType.COACH],
        "compliance_agent": agents[AgentType.COMPLIANCE],
    }
