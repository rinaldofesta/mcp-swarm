"""Tests for MCP-to-MCP bridge protocol."""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

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


class TestMessageTypes:
    """Test message type enumerations."""

    def test_message_type_values(self) -> None:
        """Test that message types have correct string values."""
        assert MessageType.HANDSHAKE_REQUEST.value == "handshake_request"
        assert MessageType.HANDSHAKE_RESPONSE.value == "handshake_response"
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.NOTIFICATION.value == "notification"
        assert MessageType.ERROR.value == "error"

    def test_message_priority_values(self) -> None:
        """Test that priority levels have correct values."""
        assert MessagePriority.LOW.value == "low"
        assert MessagePriority.NORMAL.value == "normal"
        assert MessagePriority.HIGH.value == "high"
        assert MessagePriority.URGENT.value == "urgent"


class TestBaseMessage:
    """Test base message structure."""

    def test_base_message_creation(self) -> None:
        """Test creating a base message with all fields."""
        message = BaseMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,
            payload={"test": "data"},
        )

        assert message.sender_id == "agent-1"
        assert message.receiver_id == "agent-2"
        assert message.message_type == MessageType.REQUEST
        assert message.payload == {"test": "data"}
        assert message.message_id is not None
        assert message.timestamp is not None
        assert message.priority == MessagePriority.NORMAL

    def test_base_message_auto_generated_fields(self) -> None:
        """Test that message_id and timestamp are auto-generated."""
        message1 = BaseMessage(
            sender_id="agent-1",
            message_type=MessageType.NOTIFICATION,
        )
        message2 = BaseMessage(
            sender_id="agent-1",
            message_type=MessageType.NOTIFICATION,
        )

        # Each message should have unique ID
        assert message1.message_id != message2.message_id

        # Timestamps should be valid ISO format
        datetime.fromisoformat(message1.timestamp)
        datetime.fromisoformat(message2.timestamp)

    def test_base_message_json_serialization(self) -> None:
        """Test that messages can be serialized to JSON."""
        message = BaseMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,
            payload={"key": "value"},
        )

        # Should be able to convert to JSON
        json_str = message.model_dump_json()
        data = json.loads(json_str)

        assert data["sender_id"] == "agent-1"
        assert data["receiver_id"] == "agent-2"
        assert data["message_type"] == "request"


class TestAgentCapabilities:
    """Test agent capabilities model."""

    def test_capabilities_creation(self) -> None:
        """Test creating agent capabilities."""
        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Test Agent",
            agent_role="processor",
            tools=["ping", "echo", "process_data"],
            version="0.1.0",
            metadata={"region": "us-east"},
        )

        assert caps.agent_id == "agent-1"
        assert caps.agent_name == "Test Agent"
        assert caps.agent_role == "processor"
        assert len(caps.tools) == 3
        assert "ping" in caps.tools

    def test_capabilities_with_defaults(self) -> None:
        """Test capabilities with default values."""
        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Test",
            agent_role="general",
        )

        assert caps.tools == []
        assert caps.version == "0.1.0"
        assert caps.metadata == {}


class TestHandshakeMessages:
    """Test handshake request and response messages."""

    def test_handshake_request_creation(self) -> None:
        """Test creating a handshake request."""
        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent 1",
            agent_role="processor",
        )

        request = HandshakeRequest(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=caps,
        )

        assert request.message_type == MessageType.HANDSHAKE_REQUEST
        assert request.sender_id == "agent-1"
        assert request.payload.agent_id == "agent-1"

    def test_handshake_response_creation(self) -> None:
        """Test creating a handshake response."""
        caps = AgentCapabilities(
            agent_id="agent-2",
            agent_name="Agent 2",
            agent_role="coordinator",
        )

        response = HandshakeResponse(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="request-123",
            payload=caps,
            accepted=True,
        )

        assert response.message_type == MessageType.HANDSHAKE_RESPONSE
        assert response.accepted is True
        assert response.correlation_id == "request-123"


class TestRequestResponseMessages:
    """Test request and response messages."""

    def test_request_message_creation(self) -> None:
        """Test creating a tool invocation request."""
        tool_req = ToolRequest(
            tool_name="process_data",
            arguments={"data": "test input"},
            timeout=30,
        )

        request = RequestMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=tool_req,
            priority=MessagePriority.HIGH,
        )

        assert request.message_type == MessageType.REQUEST
        assert request.payload.tool_name == "process_data"
        assert request.priority == MessagePriority.HIGH

    def test_response_message_creation(self) -> None:
        """Test creating a tool invocation response."""
        tool_resp = ToolResponse(
            success=True,
            result={"processed": True, "output": "result"},
            execution_time=0.5,
        )

        response = ResponseMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="request-123",
            payload=tool_resp,
        )

        assert response.message_type == MessageType.RESPONSE
        assert response.payload.success is True
        assert response.payload.execution_time == 0.5

    def test_error_response(self) -> None:
        """Test creating an error response."""
        tool_resp = ToolResponse(
            success=False,
            error="Tool not found",
            execution_time=0.1,
        )

        response = ResponseMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="request-123",
            payload=tool_resp,
        )

        assert response.payload.success is False
        assert response.payload.error == "Tool not found"


class TestNotificationMessages:
    """Test notification messages."""

    def test_notification_creation(self) -> None:
        """Test creating a notification message."""
        notif_msg = NotificationMessage(
            event_type="agent_status_changed",
            data={"status": "busy", "reason": "processing"},
        )

        notification = Notification(
            sender_id="agent-1",
            payload=notif_msg,
        )

        assert notification.message_type == MessageType.NOTIFICATION
        assert notification.receiver_id is None  # Broadcast
        assert notification.payload.event_type == "agent_status_changed"

    def test_targeted_notification(self) -> None:
        """Test creating a targeted notification."""
        notif_msg = NotificationMessage(
            event_type="task_complete",
            data={"task_id": "task-123"},
        )

        notification = Notification(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=notif_msg,
        )

        assert notification.receiver_id == "agent-2"


class TestErrorMessages:
    """Test error messages."""

    def test_error_message_creation(self) -> None:
        """Test creating an error message."""
        error_details = ErrorDetails(
            error_code="TOOL_NOT_FOUND",
            error_message="The requested tool does not exist",
            error_type="not_found",
            details={"tool_name": "invalid_tool"},
        )

        error_msg = ErrorMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="request-123",
            payload=error_details,
        )

        assert error_msg.message_type == MessageType.ERROR
        assert error_msg.payload.error_code == "TOOL_NOT_FOUND"
        assert error_msg.payload.error_type == "not_found"


class TestMCPBridgeProtocol:
    """Test protocol factory methods."""

    def test_create_handshake_request(self) -> None:
        """Test factory method for handshake request."""
        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent 1",
            agent_role="processor",
        )

        request = MCPBridgeProtocol.create_handshake_request(
            sender_id="agent-1",
            capabilities=caps,
            receiver_id="agent-2",
        )

        assert isinstance(request, HandshakeRequest)
        assert request.sender_id == "agent-1"
        assert request.receiver_id == "agent-2"

    def test_create_handshake_response(self) -> None:
        """Test factory method for handshake response."""
        caps = AgentCapabilities(
            agent_id="agent-2",
            agent_name="Agent 2",
            agent_role="coordinator",
        )

        response = MCPBridgeProtocol.create_handshake_response(
            sender_id="agent-2",
            receiver_id="agent-1",
            capabilities=caps,
            correlation_id="req-123",
            accepted=True,
        )

        assert isinstance(response, HandshakeResponse)
        assert response.accepted is True

    def test_create_request(self) -> None:
        """Test factory method for request."""
        tool_req = ToolRequest(
            tool_name="echo",
            arguments={"message": "hello"},
        )

        request = MCPBridgeProtocol.create_request(
            sender_id="agent-1",
            receiver_id="agent-2",
            tool_request=tool_req,
            priority=MessagePriority.URGENT,
        )

        assert isinstance(request, RequestMessage)
        assert request.priority == MessagePriority.URGENT

    def test_create_response(self) -> None:
        """Test factory method for response."""
        tool_resp = ToolResponse(
            success=True,
            result="hello",
        )

        response = MCPBridgeProtocol.create_response(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="req-123",
            tool_response=tool_resp,
        )

        assert isinstance(response, ResponseMessage)
        assert response.correlation_id == "req-123"

    def test_create_notification(self) -> None:
        """Test factory method for notification."""
        notif = NotificationMessage(
            event_type="test_event",
            data={"key": "value"},
        )

        notification = MCPBridgeProtocol.create_notification(
            sender_id="agent-1",
            notification=notif,
        )

        assert isinstance(notification, Notification)

    def test_create_error(self) -> None:
        """Test factory method for error."""
        error_details = ErrorDetails(
            error_code="TEST_ERROR",
            error_message="Test error message",
        )

        error = MCPBridgeProtocol.create_error(
            sender_id="agent-1",
            receiver_id="agent-2",
            error_details=error_details,
        )

        assert isinstance(error, ErrorMessage)
        assert error.payload.error_code == "TEST_ERROR"


class TestMessageValidation:
    """Test Pydantic validation."""

    def test_missing_required_fields(self) -> None:
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            BaseMessage()  # type: ignore[call-arg]

    def test_invalid_message_type(self) -> None:
        """Test that invalid message type raises error."""
        with pytest.raises(ValidationError):
            BaseMessage(
                sender_id="agent-1",
                message_type="invalid_type",  # type: ignore[arg-type]
            )
