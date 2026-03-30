"""
Simulation Module

Phase 3B Week 6: Multi-Agent Simulation & Training
"""

from .user_simulator import (
    CustomerPersonality,
    PersonalityProfile,
    PersonalityLibrary,
    UserSimulator
)

from .orchestrator import (
    ConversationStatus,
    Turn,
    SimulationReport,
    SimulationOrchestrator
)

__all__ = [
    # User Simulator
    "CustomerPersonality",
    "PersonalityProfile",
    "PersonalityLibrary",
    "UserSimulator",
    # Orchestrator
    "ConversationStatus",
    "Turn",
    "SimulationReport",
    "SimulationOrchestrator"
]
