class ToolError(Exception):
    """Base class for tool-related errors."""


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found in the registry."""


class ToolPermissionError(ToolError):
    """Raised when a tool call is not permitted for the agent."""


class ToolInputError(ToolError):
    """Raised when tool input validation fails."""
