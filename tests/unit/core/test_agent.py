"""Tests for MCPAgent."""

import pytest

from mcp_swarm import AgentStatus, MCPAgent, Settings


class TestMCPAgent:
    """Test suite for MCPAgent."""

    def test_agent_initialization(self) -> None:
        """Test agent initializes with correct configuration."""
        # Arrange & Act
        settings = Settings(agent_name="test-agent", agent_role="processor")
        agent = MCPAgent(settings=settings)

        # Assert
        assert agent.name == "test-agent"
        assert agent.role == "processor"
        assert agent.status == AgentStatus.CREATED
        assert not agent.is_running
        assert agent.mcp is not None

    def test_agent_initialization_with_defaults(self) -> None:
        """Test agent initializes with default settings."""
        # Act
        agent = MCPAgent()

        # Assert
        assert agent.name == "default-agent"  # from Settings default
        assert agent.role == "general"
        assert agent.status == AgentStatus.CREATED

    @pytest.mark.asyncio
    async def test_agent_lifecycle_start_stop(self) -> None:
        """Test agent start and stop lifecycle."""
        # Arrange
        settings = Settings(agent_name="lifecycle-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Assert initial state
        assert agent.status == AgentStatus.CREATED
        assert not agent.is_running

        # Act - Start
        await agent.start()

        # Assert running
        assert agent.status == AgentStatus.RUNNING
        assert agent.is_running

        # Act - Stop
        await agent.stop()

        # Assert stopped
        assert agent.status == AgentStatus.STOPPED
        assert not agent.is_running

    @pytest.mark.asyncio
    async def test_agent_cannot_start_twice(self) -> None:
        """Test that starting an already running agent raises error."""
        # Arrange
        settings = Settings(agent_name="double-start-test", agent_role="general")
        agent = MCPAgent(settings=settings)
        await agent.start()

        # Act & Assert
        with pytest.raises(RuntimeError, match="already running"):
            await agent.start()

        # Cleanup
        await agent.stop()

    @pytest.mark.asyncio
    async def test_agent_stop_when_not_running_is_safe(self) -> None:
        """Test that stopping a non-running agent doesn't raise error."""
        # Arrange
        settings = Settings(agent_name="stop-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Act & Assert - should not raise
        await agent.stop()

        # Agent should still be in CREATED state
        assert agent.status == AgentStatus.CREATED

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test async context manager automatically starts and stops agent."""
        # Arrange
        settings = Settings(agent_name="context-test", agent_role="general")

        # Act
        async with MCPAgent(settings=settings) as agent:
            # Assert agent is running
            assert agent.status == AgentStatus.RUNNING
            assert agent.is_running

        # Assert agent is stopped after context exit
        assert agent.status == AgentStatus.STOPPED
        assert not agent.is_running

    @pytest.mark.asyncio
    async def test_base_tools_registered(self) -> None:
        """Test that base tools are registered for all agents."""
        # Arrange & Act
        settings = Settings(agent_name="tools-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Assert
        tools = await agent.mcp.get_tools()
        tool_names = list(tools.keys())

        # Base tools should be present
        assert "ping" in tool_names
        assert "echo" in tool_names
        assert "get_status" in tool_names

    @pytest.mark.asyncio
    async def test_processor_role_specific_tools(self) -> None:
        """Test that processor role gets specific tools."""
        # Arrange & Act
        settings = Settings(agent_name="processor-test", agent_role="processor")
        agent = MCPAgent(settings=settings)

        # Assert
        tools = await agent.mcp.get_tools()
        tool_names = list(tools.keys())

        # Base tools
        assert "ping" in tool_names
        assert "echo" in tool_names
        assert "get_status" in tool_names

        # Processor-specific tools
        assert "process_data" in tool_names

    @pytest.mark.asyncio
    async def test_coordinator_role_specific_tools(self) -> None:
        """Test that coordinator role gets specific tools."""
        # Arrange & Act
        settings = Settings(agent_name="coordinator-test", agent_role="coordinator")
        agent = MCPAgent(settings=settings)

        # Assert
        tools = await agent.mcp.get_tools()
        tool_names = list(tools.keys())

        # Base tools
        assert "ping" in tool_names
        assert "echo" in tool_names
        assert "get_status" in tool_names

        # Coordinator-specific tools
        assert "coordinate_task" in tool_names

    @pytest.mark.asyncio
    async def test_process_requires_running_agent(self) -> None:
        """Test that process method requires agent to be running."""
        # Arrange
        settings = Settings(agent_name="process-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Act & Assert
        with pytest.raises(RuntimeError, match="not running"):
            await agent.process({"task": "test"})

    @pytest.mark.asyncio
    async def test_process_works_when_running(self) -> None:
        """Test that process method works when agent is running."""
        # Arrange
        settings = Settings(agent_name="process-running-test", agent_role="general")
        agent = MCPAgent(settings=settings)
        await agent.start()

        # Act
        result = await agent.process({"task": "test"})

        # Assert
        assert result is not None
        assert result["status"] == "processed"
        assert result["agent"] == "process-running-test"

        # Cleanup
        await agent.stop()

    @pytest.mark.asyncio
    async def test_collaborate_requires_running_agent(self) -> None:
        """Test that collaborate method requires agent to be running."""
        # Arrange
        settings = Settings(agent_name="collab-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Act & Assert
        with pytest.raises(RuntimeError, match="not running"):
            await agent.collaborate([])

    @pytest.mark.asyncio
    async def test_agent_status_property(self) -> None:
        """Test agent status property returns correct status."""
        # Arrange
        settings = Settings(agent_name="status-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Assert initial
        assert agent.status == AgentStatus.CREATED

        # Assert after start
        await agent.start()
        assert agent.status == AgentStatus.RUNNING

        # Assert after stop
        await agent.stop()
        assert agent.status == AgentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_is_running_property(self) -> None:
        """Test is_running property reflects agent state."""
        # Arrange
        settings = Settings(agent_name="running-prop-test", agent_role="general")
        agent = MCPAgent(settings=settings)

        # Assert initial
        assert agent.is_running is False

        # Assert after start
        await agent.start()
        assert agent.is_running is True

        # Assert after stop
        await agent.stop()
        assert agent.is_running is False
