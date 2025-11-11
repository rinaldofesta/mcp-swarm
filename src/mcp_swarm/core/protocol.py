"""MCP-to-MCP bridge protocol."""

from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class MCPMessage:
    """MCP message format."""

    message_id: str
    sender_id: str
    receiver_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: float


class MCPBridgeProtocol:
    """Protocol for MCP-to-MCP communication."""

    async def send_message(self, message: MCPMessage) -> None:
        """Send a message to another agent.

        Args:
            message: The message to send
        """
        # TODO: Implement message sending
        pass

    async def receive_message(self) -> MCPMessage:
        """Receive a message from another agent.

        Returns:
            The received message
        """
        # TODO: Implement message receiving
        raise NotImplementedError

