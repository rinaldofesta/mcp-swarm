"""Tests for agent registry."""

import pytest

from mcp_swarm.core.protocol import AgentCapabilities
from mcp_swarm.core.registry import LocalRegistry, RegistryError


class TestLocalRegistry:
    """Test local agent registry."""

    def test_register_agent(self) -> None:
        """Test registering an agent."""
        registry = LocalRegistry()

        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Test Agent",
            agent_role="processor",
            tools=["tool1", "tool2"],
        )

        registry.register(caps)

        assert registry.is_registered("agent-1")
        retrieved = registry.get("agent-1")
        assert retrieved is not None
        assert retrieved.agent_name == "Test Agent"

    def test_register_duplicate_updates(self) -> None:
        """Test that re-registering updates the agent."""
        registry = LocalRegistry()

        caps1 = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent v1",
            agent_role="processor",
        )
        caps2 = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent v2",
            agent_role="coordinator",
        )

        registry.register(caps1)
        registry.register(caps2)

        retrieved = registry.get("agent-1")
        assert retrieved is not None
        assert retrieved.agent_name == "Agent v2"
        assert retrieved.agent_role == "coordinator"

    def test_unregister_agent(self) -> None:
        """Test unregistering an agent."""
        registry = LocalRegistry()

        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Test Agent",
            agent_role="processor",
        )

        registry.register(caps)
        assert registry.is_registered("agent-1")

        registry.unregister("agent-1")
        assert not registry.is_registered("agent-1")

    def test_unregister_nonexistent_raises_error(self) -> None:
        """Test that unregistering non-existent agent raises error."""
        registry = LocalRegistry()

        with pytest.raises(RegistryError):
            registry.unregister("non-existent")

    def test_get_all_agents(self) -> None:
        """Test getting all registered agents."""
        registry = LocalRegistry()

        caps1 = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent 1",
            agent_role="processor",
        )
        caps2 = AgentCapabilities(
            agent_id="agent-2",
            agent_name="Agent 2",
            agent_role="coordinator",
        )

        registry.register(caps1)
        registry.register(caps2)

        all_agents = registry.get_all()
        assert len(all_agents) == 2
        assert "agent-1" in all_agents
        assert "agent-2" in all_agents

    def test_find_by_role(self) -> None:
        """Test finding agents by role."""
        registry = LocalRegistry()

        caps1 = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Processor 1",
            agent_role="processor",
        )
        caps2 = AgentCapabilities(
            agent_id="agent-2",
            agent_name="Processor 2",
            agent_role="processor",
        )
        caps3 = AgentCapabilities(
            agent_id="agent-3",
            agent_name="Coordinator",
            agent_role="coordinator",
        )

        registry.register(caps1)
        registry.register(caps2)
        registry.register(caps3)

        processors = registry.find_by_role("processor")
        assert len(processors) == 2
        assert all(a.agent_role == "processor" for a in processors)

        coordinators = registry.find_by_role("coordinator")
        assert len(coordinators) == 1
        assert coordinators[0].agent_name == "Coordinator"

    def test_find_by_tool(self) -> None:
        """Test finding agents by tool."""
        registry = LocalRegistry()

        caps1 = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Agent 1",
            agent_role="processor",
            tools=["tool_a", "tool_b"],
        )
        caps2 = AgentCapabilities(
            agent_id="agent-2",
            agent_name="Agent 2",
            agent_role="processor",
            tools=["tool_b", "tool_c"],
        )

        registry.register(caps1)
        registry.register(caps2)

        agents_with_tool_a = registry.find_by_tool("tool_a")
        assert len(agents_with_tool_a) == 1
        assert agents_with_tool_a[0].agent_id == "agent-1"

        agents_with_tool_b = registry.find_by_tool("tool_b")
        assert len(agents_with_tool_b) == 2

    def test_clear(self) -> None:
        """Test clearing all agents."""
        registry = LocalRegistry()

        caps = AgentCapabilities(
            agent_id="agent-1",
            agent_name="Test Agent",
            agent_role="processor",
        )

        registry.register(caps)
        assert len(registry.get_all()) == 1

        registry.clear()
        assert len(registry.get_all()) == 0
