"""
A2A (Agent-to-Agent) Communication System

This module provides agent-to-agent communication capabilities
for decentralized agent coordination.
"""

from app.a2a.protocol import (
    A2AMessage,
    A2ARequest,
    A2AResponse,
    A2AEvent,
    A2AQuery,
    MessageType,
    MessagePriority,
    AgentInfo,
)
from app.a2a.message_bus import A2AMessageBus
from app.a2a.agent_base import A2AAgent

__all__ = [
    "A2AMessage",
    "A2ARequest",
    "A2AResponse",
    "A2AEvent",
    "A2AQuery",
    "MessageType",
    "MessagePriority",
    "AgentInfo",
    "A2AMessageBus",
    "A2AAgent",
]
