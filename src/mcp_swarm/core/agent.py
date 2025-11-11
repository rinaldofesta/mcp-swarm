"""Base MCP Agent implementation."""

import asyncio
from enum import Enum
from typing import Any, Protocol

from fastmcp import FastMCP

from ..config.logging import get_logger
from ..config.settings import Settings


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentProtocol(Protocol):
    """Protocol for MCP agents."""

    async def initialize(self) -> None:
        """Initialize the agent."""
        ...

    async def process(self, context: dict[str, Any]) -> Any:
        """Process a task based on agent role."""
        ...

    async def collaborate(self, agents: list["AgentProtocol"]) -> None:
        """Collaborate with other agents."""
        ...


class MCPAgent:
    """Base MCP Agent class.

    This is the foundational class for all MCP agents in the swarm.
    Each agent operates as an independent MCP server with its own
    capabilities, state, and lifecycle.

    Supports async context manager for automatic cleanup:
        >>> async with MCPAgent(settings=settings) as agent:
        ...     # Agent is automatically started
        ...     result = await agent.call_tool("ping")
        ... # Agent is automatically stopped

    Or manual lifecycle management:
        >>> agent = MCPAgent(settings=settings)
        >>> await agent.start()
        >>> # ... do work ...
        >>> await agent.stop()
    """

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize an MCP agent.

        Args:
            settings: Configuration settings for the agent.
                     If None, default settings will be loaded from environment.
        """
        # Load settings from environment if not provided
        self.settings = settings or Settings()

        # Agent identity
        self.name = self.settings.agent_name
        self.role = self.settings.agent_role

        # Agent status
        self._status = AgentStatus.CREATED
        self._server_task: asyncio.Task[Any] | None = None
        self._error: Exception | None = None

        # Setup structured logging
        self.logger = get_logger(f"agent.{self.name}")
        self.logger.info(
            "agent_created",
            agent_name=self.name,
            agent_role=self.role,
            status=self._status.value,
        )

        # Initialize FastMCP server
        self.mcp = FastMCP(name=self.name)

        # Register tools
        self._setup_tools()

        self.logger.info("agent_initialized", agent_name=self.name)

    @property
    def status(self) -> AgentStatus:
        """Get the current agent status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Check if the agent is currently running."""
        return self._status == AgentStatus.RUNNING

    def _setup_tools(self) -> None:
        """Register MCP tools dynamically based on agent role."""
        # Register base tools available to all agents
        self._register_base_tools()

        # Register role-specific tools
        if self.role == "processor":
            self._register_processor_tools()
        elif self.role == "coordinator":
            self._register_coordinator_tools()
        # Add more role-specific tool registrations here

        # Note: get_tools() is async, so we can't get count here
        self.logger.info(
            "tools_registered",
            agent_name=self.name,
        )

    def _register_base_tools(self) -> None:
        """Register tools available to all agents."""

        @self.mcp.tool()
        async def ping() -> str:
            """Ping the agent to check if it's responsive.

            Returns:
                A pong response with agent information.
            """
            self.logger.debug("ping_received", agent_name=self.name)
            return f"pong from {self.name} (role: {self.role}, status: {self._status.value})"

        @self.mcp.tool()
        async def echo(message: str) -> str:
            """Echo back a message.

            Args:
                message: The message to echo back.

            Returns:
                The same message that was sent.
            """
            self.logger.debug("echo_received", agent_name=self.name, message=message)
            return f"[{self.name}] {message}"

        @self.mcp.tool()
        async def get_status() -> dict[str, Any]:
            """Get the current status of the agent.

            Returns:
                A dictionary containing agent status information.
            """
            self.logger.debug("status_requested", agent_name=self.name)
            # Note: Can't await here, so tools_count is not available
            return {
                "name": self.name,
                "role": self.role,
                "status": self._status.value,
                "is_running": self.is_running,
                "error": str(self._error) if self._error else None,
            }

    def _register_processor_tools(self) -> None:
        """Register tools specific to processor agents."""

        @self.mcp.tool()
        async def process_data(data: str) -> dict[str, Any]:
            """Process data according to processor logic.

            Args:
                data: The data to process.

            Returns:
                Processing results.
            """
            self.logger.info("processing_data", agent_name=self.name, data_length=len(data))
            # Placeholder processing logic
            return {
                "processed": True,
                "original_length": len(data),
                "result": f"Processed by {self.name}: {data[:50]}...",
            }

    def _register_coordinator_tools(self) -> None:
        """Register tools specific to coordinator agents."""

        @self.mcp.tool()
        async def coordinate_task(task_description: str) -> dict[str, Any]:
            """Coordinate a task across multiple agents.

            Args:
                task_description: Description of the task to coordinate.

            Returns:
                Coordination results.
            """
            self.logger.info("coordinating_task", agent_name=self.name, task=task_description)
            # Placeholder coordination logic
            return {
                "coordinated": True,
                "task": task_description,
                "coordinator": self.name,
            }

    async def start(self) -> None:
        """Start the MCP agent server.

        Raises:
            RuntimeError: If the agent is already running or in an invalid state.
        """
        if self._status == AgentStatus.RUNNING:
            raise RuntimeError(f"Agent {self.name} is already running")

        if self._status not in (AgentStatus.CREATED, AgentStatus.STOPPED):
            raise RuntimeError(
                f"Cannot start agent {self.name} from status {self._status.value}"
            )

        try:
            self._status = AgentStatus.STARTING
            self.logger.info("agent_starting", agent_name=self.name, port=self.settings.agent_port)

            # Start the MCP server (this will run indefinitely)
            # Note: In production, you'd run this in a background task
            # For now, we'll just mark it as running
            self._status = AgentStatus.RUNNING

            self.logger.info(
                "agent_started",
                agent_name=self.name,
                status=self._status.value,
                port=self.settings.agent_port,
            )

        except Exception as e:
            self._status = AgentStatus.ERROR
            self._error = e
            self.logger.error(
                "agent_start_failed",
                agent_name=self.name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def stop(self) -> None:
        """Stop the MCP agent server.

        Raises:
            RuntimeError: If the agent is not running.
        """
        if self._status != AgentStatus.RUNNING:
            self.logger.warning(
                "agent_stop_called_when_not_running",
                agent_name=self.name,
                status=self._status.value,
            )
            return

        try:
            self._status = AgentStatus.STOPPING
            self.logger.info("agent_stopping", agent_name=self.name)

            # Stop the server task if it's running
            if self._server_task and not self._server_task.done():
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

            self._status = AgentStatus.STOPPED
            self.logger.info("agent_stopped", agent_name=self.name)

        except Exception as e:
            self._status = AgentStatus.ERROR
            self._error = e
            self.logger.error(
                "agent_stop_failed",
                agent_name=self.name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def __aenter__(self) -> "MCPAgent":
        """Async context manager entry - start the agent."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - stop the agent."""
        await self.stop()

    async def process(self, context: dict[str, Any]) -> Any:
        """Process a task based on agent role.

        Args:
            context: Task context information.

        Returns:
            Processing results.
        """
        if not self.is_running:
            raise RuntimeError(f"Agent {self.name} is not running")

        self.logger.info("processing_task", agent_name=self.name, context=context)
        # TODO: Implement actual task processing logic
        return {"status": "processed", "agent": self.name}

    async def collaborate(self, agents: list[AgentProtocol]) -> None:
        """Collaborate with other agents.

        Args:
            agents: List of agents to collaborate with.
        """
        if not self.is_running:
            raise RuntimeError(f"Agent {self.name} is not running")

        self.logger.info(
            "collaboration_started",
            agent_name=self.name,
            agent_count=len(agents),
        )
        # TODO: Implement actual collaboration logic

