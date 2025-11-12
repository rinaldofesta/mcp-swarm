"""Agent-to-Agent Communication Example.

This example demonstrates:
1. Two agents communicating via handshake
2. Remote tool invocation between agents
3. Broadcasting notifications
4. Error handling in agent communication
"""

import asyncio

from mcp_swarm import MCPAgent, Settings
from mcp_swarm.core.registry import LocalRegistry
from mcp_swarm.core.transport import InMemoryTransport


async def example_handshake() -> None:
    """Demonstrate handshake between two agents."""
    print("\n" + "=" * 70)
    print("Example 1: Agent Handshake")
    print("=" * 70)

    # Create shared infrastructure
    transport = InMemoryTransport()
    registry = LocalRegistry()

    # Create two agents
    settings_a = Settings(
        agent_name="agent-a",
        agent_role="processor",
        agent_port=9001,
        log_format="pretty",
    )
    settings_b = Settings(
        agent_name="agent-b",
        agent_role="coordinator",
        agent_port=9002,
        log_format="pretty",
    )

    agent_a = MCPAgent(settings=settings_a, transport=transport, registry=registry)
    agent_b = MCPAgent(settings=settings_b, transport=transport, registry=registry)

    # Start both agents
    await agent_a.start()
    await agent_b.start()

    print(f"\n✓ Started Agent A: {agent_a.agent_id}")
    print(f"  Role: {agent_a.role}")
    print(f"✓ Started Agent B: {agent_b.agent_id}")
    print(f"  Role: {agent_b.role}")

    # Perform handshake
    print("\n→ Agent A sending handshake to Agent B...")
    response = await agent_a.send_handshake(agent_b.agent_id)

    print(f"✓ Handshake complete!")
    print(f"  Accepted: {response.accepted}")
    print(f"  Agent B Name: {response.payload.agent_name}")
    print(f"  Agent B Role: {response.payload.agent_role}")
    print(f"  Agent B Tools: {', '.join(response.payload.tools)}")

    # Clean up
    await agent_a.stop()
    await agent_b.stop()
    await transport.close()

    print("\n✓ Agents stopped")


async def example_remote_tool_invocation() -> None:
    """Demonstrate remote tool invocation."""
    print("\n" + "=" * 70)
    print("Example 2: Remote Tool Invocation")
    print("=" * 70)

    # Create shared infrastructure
    transport = InMemoryTransport()
    registry = LocalRegistry()

    # Create two agents
    settings_a = Settings(
        agent_name="client-agent",
        agent_role="general",
        agent_port=9003,
        log_format="pretty",
    )
    settings_b = Settings(
        agent_name="processor-agent",
        agent_role="processor",
        agent_port=9004,
        log_format="pretty",
    )

    agent_a = MCPAgent(settings=settings_a, transport=transport, registry=registry)
    agent_b = MCPAgent(settings=settings_b, transport=transport, registry=registry)

    # Start both agents
    await agent_a.start()
    await agent_b.start()

    print(f"\n✓ Client Agent: {agent_a.agent_id}")
    print(f"✓ Processor Agent: {agent_b.agent_id}")

    # Handshake first
    await agent_a.send_handshake(agent_b.agent_id)
    print("\n✓ Agents connected")

    # Client invokes ping tool on processor
    print("\n→ Client invoking 'ping' tool on Processor...")
    response = await agent_a.send_request(
        target_agent_id=agent_b.agent_id,
        tool_name="ping",
        arguments={},
    )

    print(f"✓ Tool response received:")
    print(f"  Success: {response.success}")
    print(f"  Result: {response.result}")
    print(f"  Execution time: {response.execution_time:.3f}s")

    # Client invokes echo tool
    print("\n→ Client invoking 'echo' tool on Processor...")
    response = await agent_a.send_request(
        target_agent_id=agent_b.agent_id,
        tool_name="echo",
        arguments={"message": "Hello from client!"},
    )

    print(f"✓ Tool response received:")
    print(f"  Result: {response.result}")

    # Client invokes process_data tool (processor-specific)
    print("\n→ Client invoking 'process_data' tool on Processor...")
    response = await agent_a.send_request(
        target_agent_id=agent_b.agent_id,
        tool_name="process_data",
        arguments={"data": "Important data to process"},
    )

    print(f"✓ Tool response received:")
    print(f"  Success: {response.success}")
    print(f"  Result: {response.result}")

    # Clean up
    await agent_a.stop()
    await agent_b.stop()
    await transport.close()

    print("\n✓ Agents stopped")


async def example_notifications() -> None:
    """Demonstrate notification broadcasting."""
    print("\n" + "=" * 70)
    print("Example 3: Notification Broadcasting")
    print("=" * 70)

    # Create shared infrastructure
    transport = InMemoryTransport()
    registry = LocalRegistry()

    # Create three agents
    settings_a = Settings(
        agent_name="coordinator",
        agent_role="coordinator",
        agent_port=9005,
        log_format="pretty",
    )
    settings_b = Settings(
        agent_name="worker-1",
        agent_role="processor",
        agent_port=9006,
        log_format="pretty",
    )
    settings_c = Settings(
        agent_name="worker-2",
        agent_role="processor",
        agent_port=9007,
        log_format="pretty",
    )

    coordinator = MCPAgent(settings=settings_a, transport=transport, registry=registry)
    worker1 = MCPAgent(settings=settings_b, transport=transport, registry=registry)
    worker2 = MCPAgent(settings=settings_c, transport=transport, registry=registry)

    # Start all agents
    await coordinator.start()
    await worker1.start()
    await worker2.start()

    print(f"\n✓ Coordinator: {coordinator.agent_id}")
    print(f"✓ Worker 1: {worker1.agent_id}")
    print(f"✓ Worker 2: {worker2.agent_id}")

    # Coordinator broadcasts a notification
    print("\n→ Coordinator broadcasting 'task_started' notification...")
    await coordinator.send_notification(
        event_type="task_started",
        data={"task_id": "task-123", "priority": "high"},
    )

    # Give workers time to process
    await asyncio.sleep(0.5)

    print("✓ Notification broadcast complete")

    # Coordinator sends targeted notification
    print("\n→ Coordinator sending targeted notification to Worker 1...")
    await coordinator.send_notification(
        event_type="task_assigned",
        data={"task_id": "task-456", "assigned_to": "worker-1"},
        target_agent_id=worker1.agent_id,
    )

    await asyncio.sleep(0.5)

    print("✓ Targeted notification sent")

    # Clean up
    await coordinator.stop()
    await worker1.stop()
    await worker2.stop()
    await transport.close()

    print("\n✓ All agents stopped")


async def example_error_handling() -> None:
    """Demonstrate error handling in communication."""
    print("\n" + "=" * 70)
    print("Example 4: Error Handling")
    print("=" * 70)

    # Create shared infrastructure
    transport = InMemoryTransport()
    registry = LocalRegistry()

    # Create two agents
    settings_a = Settings(
        agent_name="client",
        agent_role="general",
        agent_port=9008,
        log_format="pretty",
    )
    settings_b = Settings(
        agent_name="server",
        agent_role="general",
        agent_port=9009,
        log_format="pretty",
    )

    client = MCPAgent(settings=settings_a, transport=transport, registry=registry)
    server = MCPAgent(settings=settings_b, transport=transport, registry=registry)

    # Start both agents
    await client.start()
    await server.start()

    print(f"\n✓ Client: {client.agent_id}")
    print(f"✓ Server: {server.agent_id}")

    # Handshake
    await client.send_handshake(server.agent_id)

    # Try to invoke non-existent tool
    print("\n→ Client invoking non-existent tool 'invalid_tool'...")
    response = await client.send_request(
        target_agent_id=server.agent_id,
        tool_name="invalid_tool",
        arguments={},
    )

    print(f"✓ Error response received:")
    print(f"  Success: {response.success}")
    print(f"  Error: {response.error}")

    # Try tool invocation with timeout
    print("\n→ Testing timeout behavior (this will take a moment)...")
    try:
        response = await client.send_request(
            target_agent_id="non-existent-agent-id",
            tool_name="ping",
            arguments={},
            timeout=2.0,  # Short timeout
        )
        print("✗ Should have timed out!")
    except TimeoutError:
        print("✓ Request timed out as expected")

    # Clean up
    await client.stop()
    await server.stop()
    await transport.close()

    print("\n✓ Agents stopped")


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MCP-Swarm Agent Communication Examples")
    print("=" * 70)

    # Run examples
    await example_handshake()
    await example_remote_tool_invocation()
    await example_notifications()
    await example_error_handling()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
