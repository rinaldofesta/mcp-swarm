"""MCP-Swarm: Distributed AI Agent Orchestration via Model Context Protocol."""

__version__ = "0.1.0"

from mcp_swarm.config.logging import configure_logging, get_logger
from mcp_swarm.config.settings import Settings
from mcp_swarm.core.agent import AgentStatus, MCPAgent
from mcp_swarm.core.orchestrator import Orchestrator
from mcp_swarm.core.protocol import (
    AgentCapabilities,
    BaseMessage,
    ErrorDetails,
    ErrorMessage,
    HandshakeRequest,
    HandshakeResponse,
    MCPBridgeProtocol,
    MessagePriority,
    MessageType,
    Notification,
    NotificationMessage,
    RequestMessage,
    ResponseMessage,
    ToolRequest,
    ToolResponse,
)
from mcp_swarm.core.validator import (
    MessageTypeRegistry,
    MessageValidationError,
    MessageValidator,
    validate_message,
)

# Initialize logging with default settings on package import
# This can be reconfigured by users if needed
_settings = Settings()
configure_logging(
    log_level=_settings.log_level,
    log_format=_settings.log_format,
    service_name=_settings.service_name,
)

__all__ = [
    # Core
    "AgentStatus",
    "MCPAgent",
    "Orchestrator",
    # Configuration
    "Settings",
    "configure_logging",
    "get_logger",
    # Protocol
    "AgentCapabilities",
    "BaseMessage",
    "ErrorDetails",
    "ErrorMessage",
    "HandshakeRequest",
    "HandshakeResponse",
    "MCPBridgeProtocol",
    "MessagePriority",
    "MessageType",
    "Notification",
    "NotificationMessage",
    "RequestMessage",
    "ResponseMessage",
    "ToolRequest",
    "ToolResponse",
    # Validation
    "MessageTypeRegistry",
    "MessageValidationError",
    "MessageValidator",
    "validate_message",
    # Version
    "__version__",
]

