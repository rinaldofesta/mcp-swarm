"""Transport layer for agent-to-agent communication.

This module provides the transport abstraction for sending messages between agents.
It includes an abstract base class and an in-memory implementation for local testing.
"""

import asyncio
from abc import ABC, abstractmethod

from mcp_swarm.config.logging import get_logger
from mcp_swarm.core.protocol import BaseMessage

logger = get_logger(__name__)


class Transport(ABC):
    """Abstract base class for message transport.

    This defines the interface that all transport implementations must follow.
    Future implementations might include HTTP, WebSocket, gRPC, etc.
    """

    @abstractmethod
    async def send(self, message: BaseMessage) -> None:
        """Send a message to its destination.

        Args:
            message: The message to send

        Raises:
            TransportError: If message delivery fails
        """
        pass

    @abstractmethod
    async def receive(self, agent_id: str, timeout: float | None = None) -> BaseMessage:
        """Receive a message for a specific agent.

        Args:
            agent_id: ID of the agent receiving the message
            timeout: Optional timeout in seconds

        Returns:
            The received message

        Raises:
            asyncio.TimeoutError: If timeout is exceeded
            TransportError: If receive fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport and clean up resources."""
        pass


class TransportError(Exception):
    """Exception raised for transport-related errors."""

    pass


class InMemoryTransport(Transport):
    """In-memory transport for local agent communication.

    This transport uses asyncio queues to pass messages between agents
    running in the same process. It's useful for testing and local development.

    Each agent has a dedicated message queue identified by agent_id.
    """

    def __init__(self) -> None:
        """Initialize the in-memory transport."""
        self._queues: dict[str, asyncio.Queue[BaseMessage]] = {}
        self._closed = False
        self.logger = get_logger(f"{__name__}.InMemoryTransport")

    def _get_queue(self, agent_id: str) -> asyncio.Queue[BaseMessage]:
        """Get or create a queue for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            The agent's message queue
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            self.logger.debug("created_queue", agent_id=agent_id)
        return self._queues[agent_id]

    async def send(self, message: BaseMessage) -> None:
        """Send a message to the recipient's queue.

        Args:
            message: The message to send

        Raises:
            TransportError: If transport is closed or receiver_id is missing
        """
        if self._closed:
            raise TransportError("Transport is closed")

        if message.receiver_id is None:
            # Broadcast message to all agents
            self.logger.debug(
                "broadcasting_message",
                message_id=message.message_id,
                sender_id=message.sender_id,
                message_type=message.message_type,
                queue_count=len(self._queues),
            )
            for agent_id, queue in self._queues.items():
                # Don't send to self
                if agent_id != message.sender_id:
                    await queue.put(message)
        else:
            # Send to specific agent
            queue = self._get_queue(message.receiver_id)
            await queue.put(message)
            self.logger.debug(
                "sent_message",
                message_id=message.message_id,
                sender_id=message.sender_id,
                receiver_id=message.receiver_id,
                message_type=message.message_type,
            )

    async def receive(self, agent_id: str, timeout: float | None = None) -> BaseMessage:
        """Receive a message from the agent's queue.

        Args:
            agent_id: ID of the agent receiving the message
            timeout: Optional timeout in seconds

        Returns:
            The received message

        Raises:
            asyncio.TimeoutError: If timeout is exceeded
            TransportError: If transport is closed
        """
        if self._closed:
            raise TransportError("Transport is closed")

        queue = self._get_queue(agent_id)

        try:
            if timeout is not None:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
            else:
                message = await queue.get()

            self.logger.debug(
                "received_message",
                message_id=message.message_id,
                receiver_id=agent_id,
                sender_id=message.sender_id,
                message_type=message.message_type,
            )
            return message

        except TimeoutError:
            self.logger.warning(
                "receive_timeout",
                agent_id=agent_id,
                timeout=timeout,
            )
            raise

    async def close(self) -> None:
        """Close the transport and clear all queues."""
        if self._closed:
            return

        self._closed = True
        self._queues.clear()
        self.logger.info("transport_closed")

    def has_messages(self, agent_id: str) -> bool:
        """Check if an agent has pending messages.

        Args:
            agent_id: Agent identifier

        Returns:
            True if the agent has messages waiting
        """
        if agent_id not in self._queues:
            return False
        return not self._queues[agent_id].empty()

    def message_count(self, agent_id: str) -> int:
        """Get the number of pending messages for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of pending messages
        """
        if agent_id not in self._queues:
            return 0
        return self._queues[agent_id].qsize()
