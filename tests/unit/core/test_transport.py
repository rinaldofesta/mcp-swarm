"""Tests for transport layer."""

import asyncio

import pytest

from mcp_swarm.core.protocol import BaseMessage, MessageType
from mcp_swarm.core.transport import InMemoryTransport, TransportError


class TestInMemoryTransport:
    """Test in-memory transport."""

    @pytest.mark.asyncio
    async def test_send_and_receive(self) -> None:
        """Test basic send and receive."""
        transport = InMemoryTransport()

        message = BaseMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.NOTIFICATION,
        )

        await transport.send(message)
        received = await transport.receive("agent-2", timeout=1.0)

        assert received.message_id == message.message_id
        assert received.sender_id == "agent-1"
        assert received.receiver_id == "agent-2"

        await transport.close()

    @pytest.mark.asyncio
    async def test_receive_timeout(self) -> None:
        """Test receive timeout."""
        transport = InMemoryTransport()

        with pytest.raises(TimeoutError):
            await transport.receive("agent-1", timeout=0.1)

        await transport.close()

    @pytest.mark.asyncio
    async def test_broadcast_message(self) -> None:
        """Test broadcasting to multiple agents."""
        transport = InMemoryTransport()

        # Initialize queues for agents by getting them
        transport._get_queue("agent-2")
        transport._get_queue("agent-3")

        # Create broadcast message (no receiver_id)
        message = BaseMessage(
            sender_id="agent-1",
            receiver_id=None,
            message_type=MessageType.NOTIFICATION,
        )

        await transport.send(message)

        # Agent 2 and 3 should receive (not agent 1)
        received_2 = await transport.receive("agent-2", timeout=1.0)
        received_3 = await transport.receive("agent-3", timeout=1.0)

        assert received_2.message_id == message.message_id
        assert received_3.message_id == message.message_id

        await transport.close()

    @pytest.mark.asyncio
    async def test_transport_closed_error(self) -> None:
        """Test operations on closed transport."""
        transport = InMemoryTransport()
        await transport.close()

        message = BaseMessage(
            sender_id="agent-1",
            receiver_id="agent-2",
            message_type=MessageType.NOTIFICATION,
        )

        with pytest.raises(TransportError):
            await transport.send(message)

        with pytest.raises(TransportError):
            await transport.receive("agent-1")

    @pytest.mark.asyncio
    async def test_has_messages(self) -> None:
        """Test checking for pending messages."""
        transport = InMemoryTransport()

        assert not transport.has_messages("agent-1")

        message = BaseMessage(
            sender_id="agent-2",
            receiver_id="agent-1",
            message_type=MessageType.NOTIFICATION,
        )
        await transport.send(message)

        assert transport.has_messages("agent-1")
        assert transport.message_count("agent-1") == 1

        await transport.receive("agent-1")
        assert not transport.has_messages("agent-1")

        await transport.close()
