"""Message validation layer for MCP-Swarm.

This module provides runtime validation for messages beyond Pydantic schema validation.
It includes business logic validation, message type registry, and structured error reporting.
"""

from typing import Any, TypeVar

from pydantic import ValidationError as PydanticValidationError

from mcp_swarm.config.logging import get_logger
from mcp_swarm.core.protocol import (
    BaseMessage,
    ErrorMessage,
    HandshakeRequest,
    HandshakeResponse,
    MessageType,
    Notification,
    RequestMessage,
    ResponseMessage,
)

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseMessage)


class MessageValidationError(Exception):
    """Exception raised for message validation errors."""

    def __init__(self, message: str, field: str | None = None, errors: list[str] | None = None):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field name that failed validation
            errors: List of validation errors
        """
        self.field = field
        self.errors = errors or []
        super().__init__(message)


class MessageTypeRegistry:
    """Registry for supported message types and their validators.

    The registry maintains a mapping of message types to their corresponding
    Pydantic models, enabling runtime validation and type checking.
    """

    def __init__(self) -> None:
        """Initialize the message type registry."""
        self._registry: dict[MessageType, type[BaseMessage]] = {
            MessageType.HANDSHAKE_REQUEST: HandshakeRequest,
            MessageType.HANDSHAKE_RESPONSE: HandshakeResponse,
            MessageType.REQUEST: RequestMessage,
            MessageType.RESPONSE: ResponseMessage,
            MessageType.NOTIFICATION: Notification,
            MessageType.ERROR: ErrorMessage,
        }
        self.logger = get_logger(f"{__name__}.MessageTypeRegistry")

    def register(self, message_type: MessageType, model: type[BaseMessage]) -> None:
        """Register a message type with its model.

        Args:
            message_type: Message type to register
            model: Pydantic model for the message type
        """
        if message_type in self._registry:
            self.logger.warning(
                "message_type_already_registered",
                message_type=message_type,
                existing_model=self._registry[message_type].__name__,
                new_model=model.__name__,
            )
        self._registry[message_type] = model
        self.logger.info(
            "message_type_registered",
            message_type=message_type,
            model=model.__name__,
        )

    def get_model(self, message_type: MessageType) -> type[BaseMessage] | None:
        """Get the model for a message type.

        Args:
            message_type: Message type to look up

        Returns:
            Pydantic model for the message type, or None if not found
        """
        return self._registry.get(message_type)

    def is_registered(self, message_type: MessageType) -> bool:
        """Check if a message type is registered.

        Args:
            message_type: Message type to check

        Returns:
            True if the message type is registered
        """
        return message_type in self._registry

    def get_all_types(self) -> list[MessageType]:
        """Get all registered message types.

        Returns:
            List of registered message types
        """
        return list(self._registry.keys())


class MessageValidator:
    """Validator for MCP messages with business logic rules.

    This validator performs runtime validation beyond Pydantic schemas,
    including business logic validation, semantic checks, and custom rules.
    """

    def __init__(self, registry: MessageTypeRegistry | None = None, strict: bool = True) -> None:
        """Initialize the message validator.

        Args:
            registry: Message type registry to use (creates default if None)
            strict: If True, enforce strict validation rules
        """
        self.registry = registry or MessageTypeRegistry()
        self.strict = strict
        self.logger = get_logger(f"{__name__}.MessageValidator")

    def validate_message(self, message: BaseMessage) -> None:
        """Validate a message.

        This performs both schema validation (via Pydantic) and business logic
        validation (custom rules).

        Args:
            message: Message to validate

        Raises:
            MessageValidationError: If validation fails
        """
        # Check message type is registered
        if not self.registry.is_registered(message.message_type):
            raise MessageValidationError(
                f"Unsupported message type: {message.message_type}",
                field="message_type",
            )

        # Business logic validation (do this first so we can validate BaseMessage fields)
        self._validate_business_rules(message)

        # Validate message structure matches its type
        expected_model = self.registry.get_model(message.message_type)
        if expected_model and not isinstance(message, expected_model):
            raise MessageValidationError(
                f"Message type {message.message_type} must be instance of {expected_model.__name__}, "
                f"got {type(message).__name__}",
                field="message_type",
            )

        self.logger.debug(
            "message_validated",
            message_id=message.message_id,
            message_type=message.message_type,
        )

    def _validate_business_rules(self, message: BaseMessage) -> None:
        """Validate business logic rules for a message.

        Args:
            message: Message to validate

        Raises:
            MessageValidationError: If validation fails
        """
        errors: list[str] = []

        # Validate sender_id is not empty
        if not message.sender_id or not message.sender_id.strip():
            errors.append("sender_id cannot be empty")

        # Validate broadcast messages (receiver_id=None) are only NOTIFICATION or ERROR
        if message.receiver_id is None:
            if message.message_type not in (MessageType.NOTIFICATION, MessageType.ERROR):
                errors.append(
                    f"Only NOTIFICATION and ERROR messages can be broadcast (receiver_id=None), "
                    f"got {message.message_type}"
                )

        # Validate REQUEST and RESPONSE messages have receiver_id
        if message.message_type in (MessageType.REQUEST, MessageType.RESPONSE):
            if not message.receiver_id:
                errors.append(
                    f"{message.message_type} messages must have receiver_id"
                )

        # Validate RESPONSE messages have correlation_id
        if isinstance(message, ResponseMessage):
            if not message.correlation_id:
                errors.append("RESPONSE messages must have correlation_id")

        # Validate timeout values for REQUEST messages
        if isinstance(message, RequestMessage):
            timeout = message.payload.timeout
            if timeout is not None:
                if timeout <= 0:
                    errors.append("Request timeout must be positive")
                if self.strict and timeout > 300:  # 5 minutes
                    errors.append("Request timeout exceeds maximum (300s)")

        # Validate handshake protocol version
        if isinstance(message, (HandshakeRequest, HandshakeResponse)):
            version = message.payload.version
            if not version:
                errors.append("Handshake must include protocol version")
            elif self.strict:
                # Simple version format check: should be semver-like
                parts = version.split(".")
                if len(parts) != 3:
                    errors.append(
                        f"Protocol version must be in semver format (e.g., '0.1.0'), got '{version}'"
                    )

        if errors:
            raise MessageValidationError(
                f"Message validation failed: {', '.join(errors)}",
                errors=errors,
            )

    def validate_dict(self, data: dict[str, Any]) -> BaseMessage:
        """Validate a message from a dictionary.

        This attempts to parse the dictionary into the appropriate message model
        and validates it.

        Args:
            data: Dictionary representing a message

        Returns:
            Validated message instance

        Raises:
            MessageValidationError: If validation fails
        """
        try:
            # First try to parse as BaseMessage to get the message_type
            base_msg = BaseMessage(**data)
            message_type = base_msg.message_type

            # Get the specific model for this message type
            model = self.registry.get_model(message_type)
            if not model:
                raise MessageValidationError(
                    f"Unknown message type: {message_type}",
                    field="message_type",
                )

            # Parse with the specific model
            message = model(**data)

            # Validate business rules
            self.validate_message(message)

            return message

        except MessageValidationError:
            # Re-raise our validation errors
            raise
        except Exception as e:
            # Wrap Pydantic and other errors
            error_msg = str(e)
            if isinstance(e, PydanticValidationError):
                # Pydantic ValidationError
                errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
                raise MessageValidationError(
                    f"Schema validation failed: {error_msg}",
                    errors=errors,
                ) from e
            else:
                raise MessageValidationError(
                    f"Message validation failed: {error_msg}",
                ) from e

    def validate_json(self, json_str: str) -> BaseMessage:
        """Validate a message from a JSON string.

        Args:
            json_str: JSON string representing a message

        Returns:
            Validated message instance

        Raises:
            MessageValidationError: If validation fails
        """
        import json

        try:
            data = json.loads(json_str)
            return self.validate_dict(data)
        except json.JSONDecodeError as e:
            raise MessageValidationError(
                f"Invalid JSON: {e}",
                field="json",
            ) from e


# Global default validator instance
_default_validator: MessageValidator | None = None


def get_validator(strict: bool = True) -> MessageValidator:
    """Get the global default validator instance.

    Args:
        strict: If True, enforce strict validation rules

    Returns:
        Default validator instance
    """
    global _default_validator
    if _default_validator is None or _default_validator.strict != strict:
        _default_validator = MessageValidator(strict=strict)
    return _default_validator


def validate_message(message: BaseMessage, strict: bool = True) -> None:
    """Validate a message using the default validator.

    Args:
        message: Message to validate
        strict: If True, enforce strict validation rules

    Raises:
        MessageValidationError: If validation fails
    """
    validator = get_validator(strict=strict)
    validator.validate_message(message)
