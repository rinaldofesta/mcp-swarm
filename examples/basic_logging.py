"""Basic example demonstrating logging configuration.

This example shows how to use the MCP-Swarm logging system
with both JSON and pretty-print formats.
"""

import asyncio

from mcp_swarm import MCPAgent, Settings, configure_logging


async def main() -> None:
    """Demonstrate logging configuration."""
    print("=" * 60)
    print("MCP-Swarm Logging Demo")
    print("=" * 60)
    print()

    # Example 1: Pretty logging for development
    print("Example 1: Pretty logging (development mode)")
    print("-" * 60)
    configure_logging(log_level="INFO", log_format="pretty", service_name="demo")

    settings_dev = Settings(agent_name="demo-agent", agent_role="example")
    agent_dev = MCPAgent(settings=settings_dev)

    print()

    # Example 2: JSON logging for production
    print("\nExample 2: JSON logging (production mode)")
    print("-" * 60)
    configure_logging(log_level="INFO", log_format="json", service_name="demo")

    settings_prod = Settings(agent_name="prod-agent", agent_role="processor")
    agent_prod = MCPAgent(settings=settings_prod)

    print()
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
