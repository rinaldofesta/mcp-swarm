"""MCP-to-MCP bridge protocol.

This module defines the protocol for agent-to-agent communication in MCP-Swarm.
It provides a standardized message format, message types, and handshake mechanism
for agents to discover and communicate with each other.

Protocol Overview:
1. Handshake: Agents exchange capabilities and establish connection
2. Request/Response: Synchronous tool invocation pattern
3. Notification: Asynchronous event broadcasting
4. Error: Standardized error reporting

Message Flow:
    Agent A                    Agent B
       |                          |
       |--- HANDSHAKE_REQUEST --->|
       |<-- HANDSHAKE_RESPONSE ---|
       |                          |
       |--- REQUEST ------------->|
       |<-- RESPONSE --------------|
       |                          |
       |--- NOTIFICATION -------->|
       |                          |
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MessageType(str, Enum):
    """Message types for agent-to-agent communication."""

    HANDSHAKE_REQUEST = "handshake_request"
    HANDSHAKE_RESPONSE = "handshake_response"
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class MessagePriority(str, Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BaseMessage(BaseModel):
    """Base message format for all MCP-to-MCP communication.

    All messages exchanged between agents must follow this schema.
    This ensures consistent structure and enables validation.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this message",
    )
    message_type: MessageType = Field(
        description="Type of message being sent",
    )
    sender_id: str = Field(
        description="Unique identifier of the sending agent",
    )
    receiver_id: str | None = Field(
        default=None,
        description="Unique identifier of the receiving agent (None for broadcast)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when message was created",
    )
    correlation_id: str | None = Field(
        default=None,
        description="ID linking request/response pairs",
    )
    priority: MessagePriority = Field(
        default=MessagePriority.NORMAL,
        description="Priority level for message processing",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Message-specific data",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
    )


class AgentCapabilities(BaseModel):
    """Agent capabilities for handshake."""

    agent_id: str = Field(description="Unique agent identifier")
    agent_name: str = Field(description="Human-readable agent name")
    agent_role: str = Field(description="Agent role (e.g., processor, coordinator)")
    tools: list[str] = Field(
        default_factory=list,
        description="List of available tool names",
    )
    version: str = Field(
        default="0.1.0",
        description="Agent protocol version",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional agent metadata",
    )


class HandshakeRequest(BaseMessage):
    """Handshake request to establish connection with another agent."""

    message_type: MessageType = Field(
        default=MessageType.HANDSHAKE_REQUEST,
        frozen=True,
    )
    payload: AgentCapabilities = Field(  # type: ignore[assignment]
        description="Requesting agent's capabilities",
    )


class HandshakeResponse(BaseMessage):
    """Handshake response containing agent capabilities."""

    message_type: MessageType = Field(
        default=MessageType.HANDSHAKE_RESPONSE,
        frozen=True,
    )
    payload: AgentCapabilities = Field(  # type: ignore[assignment]
        description="Responding agent's capabilities",
    )
    accepted: bool = Field(
        default=True,
        description="Whether the handshake is accepted",
    )


class ToolRequest(BaseModel):
    """Request to invoke a tool on another agent."""

    tool_name: str = Field(description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool",
    )
    timeout: int | None = Field(
        default=None,
        description="Optional timeout in seconds",
    )


class RequestMessage(BaseMessage):
    """Request message for tool invocation."""

    message_type: MessageType = Field(
        default=MessageType.REQUEST,
        frozen=True,
    )
    payload: ToolRequest = Field(  # type: ignore[assignment]
        description="Tool invocation request",
    )


class ToolResponse(BaseModel):
    """Response from tool invocation."""

    success: bool = Field(description="Whether the tool invocation succeeded")
    result: Any = Field(
        default=None,
        description="Tool invocation result",
    )
    error: str | None = Field(
        default=None,
        description="Error message if invocation failed",
    )
    execution_time: float | None = Field(
        default=None,
        description="Tool execution time in seconds",
    )


class ResponseMessage(BaseMessage):
    """Response message for tool invocation."""

    message_type: MessageType = Field(
        default=MessageType.RESPONSE,
        frozen=True,
    )
    payload: ToolResponse = Field(  # type: ignore[assignment]
        description="Tool invocation response",
    )


class NotificationMessage(BaseModel):
    """Notification message for broadcasting events."""

    event_type: str = Field(description="Type of event being notified")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event data",
    )


class Notification(BaseMessage):
    """Notification for asynchronous event broadcasting."""

    message_type: MessageType = Field(
        default=MessageType.NOTIFICATION,
        frozen=True,
    )
    payload: NotificationMessage = Field(  # type: ignore[assignment]
        description="Notification data",
    )


class ErrorDetails(BaseModel):
    """Error details for error messages."""

    error_code: str = Field(description="Machine-readable error code")
    error_message: str = Field(description="Human-readable error message")
    error_type: str = Field(
        default="general",
        description="Type of error (e.g., validation, timeout, not_found)",
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error details",
    )


class ErrorMessage(BaseMessage):
    """Error message for reporting failures."""

    message_type: MessageType = Field(
        default=MessageType.ERROR,
        frozen=True,
    )
    payload: ErrorDetails = Field(  # type: ignore[assignment]
        description="Error details",
    )


class MCPBridgeProtocol:
    """Protocol for MCP-to-MCP communication.

    This class provides methods for creating and validating protocol messages.
    It serves as a factory for different message types and ensures all messages
    follow the protocol specification.
    """

    @staticmethod
    def create_handshake_request(
        sender_id: str,
        capabilities: AgentCapabilities,
        receiver_id: str | None = None,
    ) -> HandshakeRequest:
        """Create a handshake request message.

        Args:
            sender_id: ID of the requesting agent
            capabilities: Agent's capabilities
            receiver_id: Optional target agent ID

        Returns:
            HandshakeRequest message
        """
        return HandshakeRequest(
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=capabilities,
        )

    @staticmethod
    def create_handshake_response(
        sender_id: str,
        receiver_id: str,
        capabilities: AgentCapabilities,
        correlation_id: str,
        accepted: bool = True,
    ) -> HandshakeResponse:
        """Create a handshake response message.

        Args:
            sender_id: ID of the responding agent
            receiver_id: ID of the requesting agent
            capabilities: Agent's capabilities
            correlation_id: ID of the original request
            accepted: Whether handshake is accepted

        Returns:
            HandshakeResponse message
        """
        return HandshakeResponse(
            sender_id=sender_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id,
            payload=capabilities,
            accepted=accepted,
        )

    @staticmethod
    def create_request(
        sender_id: str,
        receiver_id: str,
        tool_request: ToolRequest,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> RequestMessage:
        """Create a tool invocation request message.

        Args:
            sender_id: ID of the requesting agent
            receiver_id: ID of the target agent
            tool_request: Tool invocation request
            priority: Message priority

        Returns:
            RequestMessage
        """
        return RequestMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=tool_request,
            priority=priority,
        )

    @staticmethod
    def create_response(
        sender_id: str,
        receiver_id: str,
        correlation_id: str,
        tool_response: ToolResponse,
    ) -> ResponseMessage:
        """Create a tool invocation response message.

        Args:
            sender_id: ID of the responding agent
            receiver_id: ID of the requesting agent
            correlation_id: ID of the original request
            tool_response: Tool invocation response

        Returns:
            ResponseMessage
        """
        return ResponseMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id,
            payload=tool_response,
        )

    @staticmethod
    def create_notification(
        sender_id: str,
        notification: NotificationMessage,
        receiver_id: str | None = None,
    ) -> Notification:
        """Create a notification message.

        Args:
            sender_id: ID of the notifying agent
            notification: Notification data
            receiver_id: Optional target agent (None for broadcast)

        Returns:
            Notification message
        """
        return Notification(
            sender_id=sender_id,
            receiver_id=receiver_id,
            payload=notification,
        )

    @staticmethod
    def create_error(
        sender_id: str,
        receiver_id: str,
        error_details: ErrorDetails,
        correlation_id: str | None = None,
    ) -> ErrorMessage:
        """Create an error message.

        Args:
            sender_id: ID of the agent reporting error
            receiver_id: ID of the target agent
            error_details: Error details
            correlation_id: Optional ID of related message

        Returns:
            ErrorMessage
        """
        return ErrorMessage(
            sender_id=sender_id,
            receiver_id=receiver_id,
            correlation_id=correlation_id,
            payload=error_details,
        )

