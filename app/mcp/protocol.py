"""
MCP Protocol Definitions

Defines the core data structures for Model Context Protocol communication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MCPVersion(str, Enum):
    """MCP protocol version"""
    V1_0 = "1.0"


class ResourceType(str, Enum):
    """Resource MIME types"""
    JSON = "application/json"
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    HTML = "text/html"
    BINARY = "application/octet-stream"


@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: str = ResourceType.JSON.value
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "uri": self.uri,
            "name": self.name,
            "mimeType": self.mimeType,
        }
        if self.description:
            result["description"] = self.description
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPPromptArgument:
    """MCP Prompt argument definition"""
    name: str
    description: Optional[str] = None
    required: bool = False


@dataclass
class MCPPrompt:
    """MCP Prompt template definition"""
    name: str
    description: str
    arguments: List[MCPPromptArgument] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "name": self.name,
            "description": self.description,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ],
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPToolCall:
    """MCP Tool call request"""
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """MCP Tool call result"""
    call_id: Optional[str]
    content: Union[str, Dict[str, Any], List[Any]]
    isError: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "content": self.content,
            "isError": self.isError,
        }
        if self.call_id:
            result["call_id"] = self.call_id
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPResourceContent:
    """MCP Resource content"""
    uri: str
    mimeType: str
    text: Optional[str] = None
    blob: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "uri": self.uri,
            "mimeType": self.mimeType,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            import base64
            result["blob"] = base64.b64encode(self.blob).decode("utf-8")
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPPromptMessage:
    """MCP Prompt message"""
    role: str  # "user" or "assistant"
    content: str


@dataclass
class MCPPromptResult:
    """MCP Prompt generation result"""
    messages: List[MCPPromptMessage]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in self.messages
            ]
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class MCPServerInfo:
    """MCP Server information"""
    name: str
    version: str
    protocol_version: str = MCPVersion.V1_0.value
    capabilities: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities,
        }
