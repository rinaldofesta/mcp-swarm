"""Tests for message validation layer."""

import json

import pytest

from mcp_swarm.core.protocol import (
    AgentCapabilities,
    BaseMessage,
    HandshakeRequest,
    HandshakeResponse,
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


class TestMessageTypeRegistry:
    """Test message type registry."""

    def test_default_types_registered(self) -> None:
        """Test that default message types are registered."""
        registry = MessageTypeRegistry()

        assert registry.is_registered(MessageType.HANDSHAKE_REQUEST)
        assert registry.is_registered(MessageType.HANDSHAKE_RESPONSE)
        assert registry.is_registered(MessageType.REQUEST)
        assert registry.is_registered(MessageType.RESPONSE)
        assert registry.is_registered(MessageType.NOTIFICATION)
        assert registry.is_registered(MessageType.ERROR)

    def test_get_model(self) -> None:
        """Test getting model for message type."""
        registry = MessageTypeRegistry()

        model = registry.get_model(MessageType.HANDSHAKE_REQUEST)
        assert model == HandshakeRequest

        model = registry.get_model(MessageType.RESPONSE)
        assert model == ResponseMessage

    def test_get_all_types(self) -> None:
        """Test getting all registered types."""
        registry = MessageTypeRegistry()

        all_types = registry.get_all_types()
        assert len(all_types) == 6
        assert MessageType.REQUEST in all_types
        assert MessageType.NOTIFICATION in all_types

    def test_register_custom_type(self) -> None:
        """Test registering a custom message type."""
        registry = MessageTypeRegistry()

        # Register a new type (reusing existing model for test)
        custom_type = MessageType.NOTIFICATION
        registry.register(custom_type, Notification)

        assert registry.is_registered(custom_type)
        assert registry.get_model(custom_type) == Notification


class TestMessageValidator:
    """Test message validator."""

    def test_validate_valid_request_message(self) -> None:
        """Test validating a valid request message."""
        validator = MessageValidator()

        message = RequestMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=ToolRequest(
                tool_name="test_tool",
                arguments={"arg1": "value1"},
                timeout=30,
            ),
        )

        # Should not raise
        validator.validate_message(message)

    def test_validate_valid_response_message(self) -> None:
        """Test validating a valid response message."""
        validator = MessageValidator()

        message = ResponseMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id="request-123",
            payload=ToolResponse(
                success=True,
                result={"status": "ok"},
                execution_time=0.5,
            ),
        )

        # Should not raise
        validator.validate_message(message)

    def test_validate_valid_notification_broadcast(self) -> None:
        """Test validating a broadcast notification."""
        validator = MessageValidator()

        message = Notification(
            sender_id="agent-1",
            receiver_id=None,  # Broadcast
            payload=NotificationMessage(
                event_type="task_started",
                data={"task_id": "123"},
            ),
        )

        # Should not raise
        validator.validate_message(message)

    def test_validate_empty_sender_id(self) -> None:
        """Test that empty sender_id fails validation."""
        validator = MessageValidator()

        message = BaseMessage(
            sender_id="",  # Empty
            receiver_id="agent-2",
            message_type=MessageType.NOTIFICATION,
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "sender_id cannot be empty" in str(exc_info.value)

    def test_validate_broadcast_non_notification(self) -> None:
        """Test that only NOTIFICATION and ERROR can be broadcast."""
        validator = MessageValidator()

        # Try to broadcast a REQUEST (should fail)
        message = RequestMessage(
            sender_id="agent-1",
            receiver_id=None,  # Broadcast
            payload=ToolRequest(tool_name="test", arguments={}),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "Only NOTIFICATION and ERROR messages can be broadcast" in str(exc_info.value)

    def test_validate_request_missing_receiver(self) -> None:
        """Test that REQUEST messages must have receiver_id."""
        validator = MessageValidator()

        message = RequestMessage(
            sender_id="agent-1",
            receiver_id="",  # Empty (falsy)
            payload=ToolRequest(tool_name="test", arguments={}),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "REQUEST messages must have receiver_id" in str(exc_info.value)

    def test_validate_response_missing_correlation_id(self) -> None:
        """Test that RESPONSE messages must have correlation_id."""
        validator = MessageValidator()

        message = ResponseMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            correlation_id=None,  # Missing
            payload=ToolResponse(success=True, result={}, execution_time=0.1),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "RESPONSE messages must have correlation_id" in str(exc_info.value)

    def test_validate_request_timeout_negative(self) -> None:
        """Test that request timeout must be positive."""
        validator = MessageValidator()

        message = RequestMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=ToolRequest(
                tool_name="test",
                arguments={},
                timeout=-5,  # Negative
            ),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "Request timeout must be positive" in str(exc_info.value)

    def test_validate_request_timeout_too_large_strict(self) -> None:
        """Test that request timeout is limited in strict mode."""
        validator = MessageValidator(strict=True)

        message = RequestMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=ToolRequest(
                tool_name="test",
                arguments={},
                timeout=400,  # Over 300s limit
            ),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "timeout exceeds maximum" in str(exc_info.value)

    def test_validate_request_timeout_lenient(self) -> None:
        """Test that large timeout is allowed in lenient mode."""
        validator = MessageValidator(strict=False)

        message = RequestMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=ToolRequest(
                tool_name="test",
                arguments={},
                timeout=400,  # Over 300s limit, but lenient
            ),
        )

        # Should not raise in lenient mode
        validator.validate_message(message)

    def test_validate_handshake_version_format_strict(self) -> None:
        """Test that handshake version must be semver format in strict mode."""
        validator = MessageValidator(strict=True)

        message = HandshakeRequest(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=AgentCapabilities(
                agent_id="agent-1",
                agent_name="Test",
                agent_role="tester",
                version="1.0",  # Not semver (missing patch)
            ),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "semver format" in str(exc_info.value)

    def test_validate_handshake_version_lenient(self) -> None:
        """Test that version format is not checked in lenient mode."""
        validator = MessageValidator(strict=False)

        message = HandshakeRequest(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=AgentCapabilities(
                agent_id="agent-1",
                agent_name="Test",
                agent_role="tester",
                version="1.0",  # Not semver, but lenient
            ),
        )

        # Should not raise in lenient mode
        validator.validate_message(message)

    def test_validate_wrong_message_type_class(self) -> None:
        """Test that message class must match message type."""
        validator = MessageValidator()

        # Create a base message with REQUEST type but BaseMessage class
        message = BaseMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.REQUEST,  # Type says REQUEST
        )  # But class is BaseMessage, not RequestMessage

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        assert "must be instance of RequestMessage" in str(exc_info.value)

    def test_validate_dict_valid(self) -> None:
        """Test validating a message from dictionary."""
        validator = MessageValidator()

        data = {
            "sender_id": "agent-1",
            "receiver_id": "agent-2",
            "message_type": "request",
            "payload": {
                "tool_name": "test_tool",
                "arguments": {"arg1": "value1"},
                "timeout": 30,
            },
        }

        message = validator.validate_dict(data)
        assert isinstance(message, RequestMessage)
        assert message.sender_id == "agent-1"
        assert message.payload.tool_name == "test_tool"

    def test_validate_dict_invalid_schema(self) -> None:
        """Test that invalid schema raises error."""
        validator = MessageValidator()

        data = {
            "sender_id": "agent-1",
            # Missing receiver_id
            "message_type": "request",
            "payload": {
                "tool_name": "test_tool",
                # Missing arguments
            },
        }

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_dict(data)

        assert "validation failed" in str(exc_info.value).lower()

    def test_validate_json_valid(self) -> None:
        """Test validating a message from JSON string."""
        validator = MessageValidator()

        json_str = json.dumps({
            "sender_id": "agent-1",
            "receiver_id": None,
            "message_type": "notification",
            "payload": {
                "event_type": "test_event",
                "data": {"key": "value"},
            },
        })

        message = validator.validate_json(json_str)
        assert isinstance(message, Notification)
        assert message.sender_id == "agent-1"

    def test_validate_json_invalid_json(self) -> None:
        """Test that invalid JSON raises error."""
        validator = MessageValidator()

        json_str = "{invalid json"

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_json(json_str)

        assert "Invalid JSON" in str(exc_info.value)

    def test_validate_multiple_errors(self) -> None:
        """Test that multiple validation errors are collected."""
        validator = MessageValidator()

        # Multiple violations: empty sender_id, broadcast REQUEST
        message = RequestMessage(
            sender_id="  ",  # Whitespace only
            receiver_id=None,  # Broadcast REQUEST (invalid)
            payload=ToolRequest(tool_name="test", arguments={}),
        )

        with pytest.raises(MessageValidationError) as exc_info:
            validator.validate_message(message)

        error_msg = str(exc_info.value)
        # Should contain both errors
        assert "sender_id cannot be empty" in error_msg
        assert "Only NOTIFICATION and ERROR messages can be broadcast" in error_msg


class TestGlobalValidator:
    """Test global validator functions."""

    def test_validate_message_function(self) -> None:
        """Test global validate_message function."""
        message = Notification(
            sender_id="agent-1",
            receiver_id=None,
            payload=NotificationMessage(event_type="test", data={}),
        )

        # Should not raise
        validate_message(message)

    def test_validate_message_function_with_error(self) -> None:
        """Test global validate_message function with error."""
        message = BaseMessage(
            sender_id="",  # Empty
            message_type=MessageType.NOTIFICATION,
        )

        with pytest.raises(MessageValidationError):
            validate_message(message)

    def test_validate_message_strict_mode(self) -> None:
        """Test global validator in strict mode."""
        message = HandshakeRequest(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=AgentCapabilities(
                agent_id="agent-1",
                agent_name="Test",
                agent_role="tester",
                version="bad-version",  # Invalid semver
            ),
        )

        with pytest.raises(MessageValidationError):
            validate_message(message, strict=True)

    def test_validate_message_lenient_mode(self) -> None:
        """Test global validator in lenient mode."""
        message = HandshakeRequest(
            sender_id="agent-1",
            receiver_id="agent-2",
            payload=AgentCapabilities(
                agent_id="agent-1",
                agent_name="Test",
                agent_role="tester",
                version="bad-version",  # Invalid semver, but lenient
            ),
        )

        # Should not raise in lenient mode
        validate_message(message, strict=False)
