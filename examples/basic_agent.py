"""Basic MCP Agent Example.

This example demonstrates:
1. Creating an agent with different roles
2. Starting and stopping agents
3. Using the async context manager
4. Checking agent status and available tools
"""

import asyncio

from mcp_swarm import MCPAgent, Settings


async def example_manual_lifecycle() -> None:
    """Demonstrate manual agent lifecycle management."""
    print("\n" + "=" * 60)
    print("Example 1: Manual Lifecycle Management")
    print("=" * 60)

    # Create a processor agent
    settings = Settings(
        agent_name="data-processor",
        agent_role="processor",
        agent_port=8001,
        log_format="pretty",
    )
    agent = MCPAgent(settings=settings)

    print(f"\n✓ Agent created: {agent.name}")
    print(f"  Status: {agent.status.value}")
    print(f"  Role: {agent.role}")

    # List available tools
    tools = await agent.mcp.get_tools()
    print(f"  Tools: {len(tools)}")
    print("\n  Available tools:")
    for tool_name, tool in tools.items():
        print(f"    - {tool_name}: {tool.description}")

    # Start the agent
    await agent.start()
    print("\n✓ Agent started")
    print(f"  Status: {agent.status.value}")
    print(f"  Is running: {agent.is_running}")

    # Simulate some work
    await asyncio.sleep(1)

    # Stop the agent
    await agent.stop()
    print("\n✓ Agent stopped")
    print(f"  Status: {agent.status.value}")


async def example_context_manager() -> None:
    """Demonstrate automatic lifecycle with context manager."""
    print("\n" + "=" * 60)
    print("Example 2: Async Context Manager (Automatic Lifecycle)")
    print("=" * 60)

    settings = Settings(
        agent_name="coordinator-agent",
        agent_role="coordinator",
        agent_port=8002,
        log_format="pretty",
    )

    async with MCPAgent(settings=settings) as agent:
        print(f"\n✓ Agent auto-started: {agent.name}")
        print(f"  Status: {agent.status.value}")
        print(f"  Is running: {agent.is_running}")

        # List coordinator-specific tools
        tools = await agent.mcp.get_tools()
        print("\n  Available tools:")
        for tool_name in tools.keys():
            print(f"    - {tool_name}")

        await asyncio.sleep(1)

    print("\n✓ Agent auto-stopped")
    print(f"  Status: {agent.status.value}")


async def example_multiple_agents() -> None:
    """Demonstrate running multiple agents."""
    print("\n" + "=" * 60)
    print("Example 3: Multiple Agents with Different Roles")
    print("=" * 60)

    # Create multiple agents with different roles
    processor_settings = Settings(
        agent_name="processor-1",
        agent_role="processor",
        agent_port=8003,
        log_format="pretty",
    )

    coordinator_settings = Settings(
        agent_name="coordinator-1",
        agent_role="coordinator",
        agent_port=8004,
        log_format="pretty",
    )

    general_settings = Settings(
        agent_name="general-1",
        agent_role="general",
        agent_port=8005,
        log_format="pretty",
    )

    # Create agents
    processor = MCPAgent(settings=processor_settings)
    coordinator = MCPAgent(settings=coordinator_settings)
    general = MCPAgent(settings=general_settings)

    agents = [processor, coordinator, general]

    # Start all agents
    for agent in agents:
        await agent.start()
        tools = await agent.mcp.get_tools()
        print(f"✓ Started {agent.name} ({agent.role})")
        print(f"  Tools: {list(tools.keys())}")

    print(f"\n✓ All {len(agents)} agents running")

    # Simulate work
    await asyncio.sleep(1)

    # Stop all agents
    for agent in agents:
        await agent.stop()
        print(f"✓ Stopped {agent.name}")


async def example_error_handling() -> None:
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("Example 4: Error Handling")
    print("=" * 60)

    settings = Settings(
        agent_name="test-agent",
        agent_role="general",
        agent_port=8006,
        log_format="pretty",
    )
    agent = MCPAgent(settings=settings)

    # Try to start twice (should raise error)
    await agent.start()
    print(f"✓ Agent started: {agent.name}")

    try:
        await agent.start()
        print("✗ Should have raised RuntimeError!")
    except RuntimeError as e:
        print(f"✓ Caught expected error: {e}")

    await agent.stop()
    print("✓ Agent stopped")

    # Try to stop when not running (should log warning but not error)
    await agent.stop()
    print("✓ Stop called when not running (no error)")


async def main() -> None:
    """Run all examples."""
    print("\n" + "=" * 60)
    print("MCP-Swarm Agent Examples")
    print("=" * 60)

    # Run examples
    await example_manual_lifecycle()
    await example_context_manager()
    await example_multiple_agents()
    await example_error_handling()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
