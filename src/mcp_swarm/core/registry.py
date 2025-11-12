"""Agent discovery and registration.

This module provides both local (in-memory) and remote (MCP Registry) agent registration.
The local registry is used for agent-to-agent communication within the same process,
while the remote registry will be used for distributed agent discovery.
"""

from typing import Any

from mcp_swarm.config.logging import get_logger
from mcp_swarm.core.protocol import AgentCapabilities

logger = get_logger(__name__)


class RegistryError(Exception):
    """Exception raised for registry-related errors."""

    pass


class LocalRegistry:
    """In-memory registry for local agent discovery.

    This registry maintains a mapping of agent IDs to their capabilities
    and provides lookup functionality for agent-to-agent communication
    within the same process.
    """

    def __init__(self) -> None:
        """Initialize the local registry."""
        self._agents: dict[str, AgentCapabilities] = {}
        self.logger = get_logger(f"{__name__}.LocalRegistry")

    def register(self, capabilities: AgentCapabilities) -> None:
        """Register an agent with the local registry.

        Args:
            capabilities: Agent capabilities including ID, name, role, tools

        Raises:
            RegistryError: If agent is already registered
        """
        agent_id = capabilities.agent_id

        if agent_id in self._agents:
            self.logger.warning(
                "agent_already_registered",
                agent_id=agent_id,
                agent_name=capabilities.agent_name,
            )
            # Update instead of raising error
            self._agents[agent_id] = capabilities
            self.logger.info(
                "agent_updated",
                agent_id=agent_id,
                agent_name=capabilities.agent_name,
                agent_role=capabilities.agent_role,
                tool_count=len(capabilities.tools),
            )
        else:
            self._agents[agent_id] = capabilities
            self.logger.info(
                "agent_registered",
                agent_id=agent_id,
                agent_name=capabilities.agent_name,
                agent_role=capabilities.agent_role,
                tool_count=len(capabilities.tools),
            )

    def unregister(self, agent_id: str) -> None:
        """Unregister an agent from the local registry.

        Args:
            agent_id: Agent identifier

        Raises:
            RegistryError: If agent is not registered
        """
        if agent_id not in self._agents:
            raise RegistryError(f"Agent not registered: {agent_id}")

        agent = self._agents.pop(agent_id)
        self.logger.info(
            "agent_unregistered",
            agent_id=agent_id,
            agent_name=agent.agent_name,
        )

    def get(self, agent_id: str) -> AgentCapabilities | None:
        """Get an agent's capabilities by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent capabilities if found, None otherwise
        """
        return self._agents.get(agent_id)

    def get_all(self) -> dict[str, AgentCapabilities]:
        """Get all registered agents.

        Returns:
            Dictionary mapping agent IDs to their capabilities
        """
        return self._agents.copy()

    def find_by_role(self, role: str) -> list[AgentCapabilities]:
        """Find all agents with a specific role.

        Args:
            role: Agent role to search for

        Returns:
            List of matching agent capabilities
        """
        return [
            agent for agent in self._agents.values() if agent.agent_role == role
        ]

    def find_by_tool(self, tool_name: str) -> list[AgentCapabilities]:
        """Find all agents that have a specific tool.

        Args:
            tool_name: Tool name to search for

        Returns:
            List of matching agent capabilities
        """
        return [
            agent for agent in self._agents.values() if tool_name in agent.tools
        ]

    def is_registered(self, agent_id: str) -> bool:
        """Check if an agent is registered.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent is registered
        """
        return agent_id in self._agents

    def clear(self) -> None:
        """Clear all registered agents."""
        count = len(self._agents)
        self._agents.clear()
        self.logger.info("registry_cleared", agent_count=count)


class Registry:
    """MCP Registry client for distributed agent discovery.

    This will be implemented in DISC-001 to connect to the MCP Registry API
    for discovering agents across different processes/machines.
    """

    def __init__(self, registry_url: str, api_key: str | None = None) -> None:
        """Initialize the registry client.

        Args:
            registry_url: URL of the MCP registry
            api_key: Optional API key for authentication
        """
        self.registry_url = registry_url
        self.api_key = api_key
        self.logger = get_logger(f"{__name__}.Registry")

    async def register_agent(self, agent_id: str, metadata: dict[str, Any]) -> None:
        """Register an agent with the remote registry.

        Args:
            agent_id: Unique identifier for the agent
            metadata: Agent metadata (capabilities, role, etc.)
        """
        # TODO: Implement in DISC-001
        self.logger.warning(
            "remote_registry_not_implemented",
            agent_id=agent_id,
        )

    async def discover_agents(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Discover available agents from the remote registry.

        Args:
            filters: Optional filters for discovery (role, capabilities, etc.)

        Returns:
            List of discovered agents with their metadata
        """
        # TODO: Implement in DISC-001
        self.logger.warning("remote_registry_not_implemented")
        return []
