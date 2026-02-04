"""
A2A (Agent-to-Agent) Protocol Definitions

Defines the message protocol for agent-to-agent communication.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageType(str, Enum):
    """Agent message types"""
    REQUEST = "request"  # Request for action/information
    RESPONSE = "response"  # Response to a request
    EVENT = "event"  # Event notification (broadcast)
    QUERY = "query"  # Query for information
    COMMAND = "command"  # Command to execute
    ACK = "ack"  # Acknowledgment


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class A2AMessage:
    """
    Agent-to-Agent Message

    Standard message format for inter-agent communication.
    """

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.REQUEST
    from_agent: str = ""
    to_agent: Optional[str] = None  # None = broadcast
    conversation_id: str = ""
    timestamp: float = field(default_factory=time.time)
    payload: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None  # ID of message being replied to
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    ttl: Optional[int] = None  # Time-to-live in seconds
    requires_ack: bool = False  # Whether acknowledgment is required

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "reply_to": self.reply_to,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "ttl": self.ttl,
            "requires_ack": self.requires_ack,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> A2AMessage:
        """Create from dictionary"""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=MessageType(data.get("message_type", "request")),
            from_agent=data.get("from_agent", ""),
            to_agent=data.get("to_agent"),
            conversation_id=data.get("conversation_id", ""),
            timestamp=data.get("timestamp", time.time()),
            payload=data.get("payload", {}),
            reply_to=data.get("reply_to"),
            priority=MessagePriority(data.get("priority", "normal")),
            metadata=data.get("metadata", {}),
            ttl=data.get("ttl"),
            requires_ack=data.get("requires_ack", False),
        )

    def create_response(
        self, payload: Dict[str, Any], from_agent: str
    ) -> A2AMessage:
        """
        Create a response message to this message

        Args:
            payload: Response payload
            from_agent: Agent sending the response

        Returns:
            Response message
        """
        return A2AMessage(
            message_type=MessageType.RESPONSE,
            from_agent=from_agent,
            to_agent=self.from_agent,
            conversation_id=self.conversation_id,
            payload=payload,
            reply_to=self.message_id,
            priority=self.priority,
        )

    def create_ack(self, from_agent: str) -> A2AMessage:
        """
        Create an acknowledgment message

        Args:
            from_agent: Agent sending the ACK

        Returns:
            ACK message
        """
        return A2AMessage(
            message_type=MessageType.ACK,
            from_agent=from_agent,
            to_agent=self.from_agent,
            conversation_id=self.conversation_id,
            payload={"ack_for": self.message_id},
            reply_to=self.message_id,
        )


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None


@dataclass
class AgentInfo:
    """Agent information for registry"""
    agent_id: str
    agent_type: str
    capabilities: List[str] = field(default_factory=list)
    status: str = "online"  # online, offline, busy
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "status": self.status,
            "metadata": self.metadata,
            "last_seen": self.last_seen,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentInfo:
        """Create from dictionary"""
        return cls(
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            capabilities=data.get("capabilities", []),
            status=data.get("status", "online"),
            metadata=data.get("metadata", {}),
            last_seen=data.get("last_seen", time.time()),
            version=data.get("version", "1.0.0"),
        )


@dataclass
class A2ARequest:
    """Convenience wrapper for request messages"""
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0

    def to_message(
        self, from_agent: str, to_agent: str, conversation_id: str
    ) -> A2AMessage:
        """Convert to A2A message"""
        return A2AMessage(
            message_type=MessageType.REQUEST,
            from_agent=from_agent,
            to_agent=to_agent,
            conversation_id=conversation_id,
            payload={
                "action": self.action,
                "parameters": self.parameters,
            },
            metadata={"timeout": self.timeout},
            requires_ack=True,
        )


@dataclass
class A2AResponse:
    """Convenience wrapper for response messages"""
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """Convert to payload dictionary"""
        payload = {
            "success": self.success,
            "metadata": self.metadata,
        }
        if self.result is not None:
            payload["result"] = self.result
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass
class A2AEvent:
    """Convenience wrapper for event messages"""
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_message(
        self, from_agent: str, conversation_id: str, to_agent: Optional[str] = None
    ) -> A2AMessage:
        """Convert to A2A message"""
        return A2AMessage(
            message_type=MessageType.EVENT,
            from_agent=from_agent,
            to_agent=to_agent,  # None = broadcast
            conversation_id=conversation_id,
            payload={
                "event_type": self.event_type,
                "data": self.data,
            },
        )


@dataclass
class A2AQuery:
    """Convenience wrapper for query messages"""
    query: str
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 10

    def to_message(
        self, from_agent: str, to_agent: str, conversation_id: str
    ) -> A2AMessage:
        """Convert to A2A message"""
        return A2AMessage(
            message_type=MessageType.QUERY,
            from_agent=from_agent,
            to_agent=to_agent,
            conversation_id=conversation_id,
            payload={
                "query": self.query,
                "filters": self.filters,
                "limit": self.limit,
            },
        )
