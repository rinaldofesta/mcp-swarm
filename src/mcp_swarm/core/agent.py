"""Base MCP Agent implementation."""

import asyncio
import time
from enum import Enum
from typing import Any, Protocol

from fastmcp import FastMCP

from ..config.logging import get_logger
from ..config.settings import Settings
from .protocol import (
    AgentCapabilities,
    HandshakeRequest,
    HandshakeResponse,
    MCPBridgeProtocol,
    MessagePriority,
    MessageType,
    NotificationMessage,
    RequestMessage,
    ResponseMessage,
    ToolRequest,
    ToolResponse,
)
from .registry import LocalRegistry
from .transport import InMemoryTransport, Transport


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

    def __init__(
        self,
        settings: Settings | None = None,
        transport: Transport | None = None,
        registry: LocalRegistry | None = None,
    ) -> None:
        """Initialize an MCP agent.

        Args:
            settings: Configuration settings for the agent.
                     If None, default settings will be loaded from environment.
            transport: Transport layer for message passing.
                      If None, a new InMemoryTransport will be created.
            registry: Agent registry for discovery.
                     If None, a new LocalRegistry will be created.
        """
        # Load settings from environment if not provided
        self.settings = settings or Settings()

        # Agent identity
        self.name = self.settings.agent_name
        self.role = self.settings.agent_role
        self.agent_id = f"{self.name}-{id(self)}"  # Unique ID for this instance

        # Agent status
        self._status = AgentStatus.CREATED
        self._server_task: asyncio.Task[Any] | None = None
        self._message_handler_task: asyncio.Task[Any] | None = None
        self._error: Exception | None = None

        # Communication infrastructure
        self.transport = transport or InMemoryTransport()
        self.registry = registry or LocalRegistry()

        # Connection tracking
        self._connected_agents: dict[str, AgentCapabilities] = {}
        self._pending_requests: dict[str, asyncio.Future[ResponseMessage]] = {}

        # Setup structured logging
        self.logger = get_logger(f"agent.{self.name}")
        self.logger.info(
            "agent_created",
            agent_id=self.agent_id,
            agent_name=self.name,
            agent_role=self.role,
            status=self._status.value,
        )

        # Initialize FastMCP server
        self.mcp = FastMCP(name=self.name)

        # Register tools
        self._setup_tools()

        self.logger.info("agent_initialized", agent_id=self.agent_id, agent_name=self.name)

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
            self.logger.info("agent_starting", agent_id=self.agent_id, agent_name=self.name, port=self.settings.agent_port)

            # Register with the local registry
            tools = await self.mcp.get_tools()
            capabilities = AgentCapabilities(
                agent_id=self.agent_id,
                agent_name=self.name,
                agent_role=self.role,
                tools=list(tools.keys()),
                version="0.1.0",
            )
            self.registry.register(capabilities)

            # Start message handler
            self._message_handler_task = asyncio.create_task(self._handle_messages())

            # Start the MCP server (this will run indefinitely)
            # Note: In production, you'd run this in a background task
            # For now, we'll just mark it as running
            self._status = AgentStatus.RUNNING

            self.logger.info(
                "agent_started",
                agent_id=self.agent_id,
                agent_name=self.name,
                status=self._status.value,
                port=self.settings.agent_port,
                tool_count=len(tools),
            )

        except Exception as e:
            self._status = AgentStatus.ERROR
            self._error = e
            self.logger.error(
                "agent_start_failed",
                agent_id=self.agent_id,
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
                agent_id=self.agent_id,
                agent_name=self.name,
                status=self._status.value,
            )
            return

        try:
            self._status = AgentStatus.STOPPING
            self.logger.info("agent_stopping", agent_id=self.agent_id, agent_name=self.name)

            # Stop message handler
            if self._message_handler_task and not self._message_handler_task.done():
                self._message_handler_task.cancel()
                try:
                    await self._message_handler_task
                except asyncio.CancelledError:
                    pass

            # Stop the server task if it's running
            if self._server_task and not self._server_task.done():
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

            # Unregister from registry
            try:
                self.registry.unregister(self.agent_id)
            except Exception as e:
                self.logger.warning("registry_unregister_failed", error=str(e))

            self._status = AgentStatus.STOPPED
            self.logger.info("agent_stopped", agent_id=self.agent_id, agent_name=self.name)

        except Exception as e:
            self._status = AgentStatus.ERROR
            self._error = e
            self.logger.error(
                "agent_stop_failed",
                agent_id=self.agent_id,
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

    # ========================================================================
    # Agent-to-Agent Communication Methods
    # ========================================================================

    async def send_handshake(self, target_agent_id: str) -> HandshakeResponse:
        """Send a handshake request to another agent.

        Args:
            target_agent_id: ID of the agent to connect with

        Returns:
            HandshakeResponse from the target agent

        Raises:
            RuntimeError: If agent is not running
            asyncio.TimeoutError: If handshake times out
        """
        if not self.is_running:
            raise RuntimeError(f"Agent {self.name} is not running")

        # Create capabilities
        tools = await self.mcp.get_tools()
        capabilities = AgentCapabilities(
            agent_id=self.agent_id,
            agent_name=self.name,
            agent_role=self.role,
            tools=list(tools.keys()),
            version="0.1.0",
        )

        # Create handshake request
        request = MCPBridgeProtocol.create_handshake_request(
            sender_id=self.agent_id,
            capabilities=capabilities,
            receiver_id=target_agent_id,
        )

        self.logger.info(
            "sending_handshake",
            target_agent_id=target_agent_id,
            message_id=request.message_id,
        )

        # Send via transport
        await self.transport.send(request)

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(
                self._wait_for_handshake_response(request.message_id),
                timeout=30.0,
            )

            # Store connection if accepted
            if response.accepted:
                self._connected_agents[target_agent_id] = response.payload
                self.logger.info(
                    "handshake_accepted",
                    target_agent_id=target_agent_id,
                    target_name=response.payload.agent_name,
                )
            else:
                self.logger.warning(
                    "handshake_rejected",
                    target_agent_id=target_agent_id,
                )

            return response

        except TimeoutError:
            self.logger.error(
                "handshake_timeout",
                target_agent_id=target_agent_id,
            )
            raise

    async def send_request(
        self,
        target_agent_id: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float = 30.0,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> ToolResponse:
        """Send a tool invocation request to another agent.

        Args:
            target_agent_id: ID of the agent to send request to
            tool_name: Name of the tool to invoke
            arguments: Tool arguments
            timeout: Request timeout in seconds
            priority: Message priority

        Returns:
            Tool response from the target agent

        Raises:
            RuntimeError: If agent is not running
            asyncio.TimeoutError: If request times out
        """
        if not self.is_running:
            raise RuntimeError(f"Agent {self.name} is not running")

        # Create tool request
        tool_request = ToolRequest(
            tool_name=tool_name,
            arguments=arguments or {},
            timeout=int(timeout),
        )

        # Create request message
        request = MCPBridgeProtocol.create_request(
            sender_id=self.agent_id,
            receiver_id=target_agent_id,
            tool_request=tool_request,
            priority=priority,
        )

        self.logger.info(
            "sending_request",
            target_agent_id=target_agent_id,
            tool_name=tool_name,
            message_id=request.message_id,
        )

        # Setup future for response
        future: asyncio.Future[ResponseMessage] = asyncio.Future()
        self._pending_requests[request.message_id] = future

        try:
            # Send via transport
            await self.transport.send(request)

            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)

            self.logger.info(
                "request_completed",
                target_agent_id=target_agent_id,
                tool_name=tool_name,
                success=response.payload.success,
            )

            return response.payload

        except TimeoutError:
            self.logger.error(
                "request_timeout",
                target_agent_id=target_agent_id,
                tool_name=tool_name,
            )
            raise
        finally:
            # Clean up pending request
            self._pending_requests.pop(request.message_id, None)

    async def send_notification(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        target_agent_id: str | None = None,
    ) -> None:
        """Send a notification to one or all agents.

        Args:
            event_type: Type of event being notified
            data: Event data
            target_agent_id: Optional target agent (None for broadcast)

        Raises:
            RuntimeError: If agent is not running
        """
        if not self.is_running:
            raise RuntimeError(f"Agent {self.name} is not running")

        # Create notification
        notif = NotificationMessage(
            event_type=event_type,
            data=data or {},
        )

        # Create notification message
        notification = MCPBridgeProtocol.create_notification(
            sender_id=self.agent_id,
            notification=notif,
            receiver_id=target_agent_id,
        )

        self.logger.info(
            "sending_notification",
            event_type=event_type,
            target_agent_id=target_agent_id or "broadcast",
        )

        # Send via transport
        await self.transport.send(notification)

    async def _wait_for_handshake_response(self, request_id: str) -> HandshakeResponse:
        """Wait for a handshake response with specific correlation ID.

        Args:
            request_id: The request message ID to wait for

        Returns:
            HandshakeResponse message
        """
        while True:
            message = await self.transport.receive(self.agent_id)

            if (
                message.message_type == MessageType.HANDSHAKE_RESPONSE
                and message.correlation_id == request_id
            ):
                return HandshakeResponse(**message.model_dump())

            # Put other messages back for the main handler
            await self.transport.send(message)
            await asyncio.sleep(0.1)  # Brief pause to avoid tight loop

    async def _handle_messages(self) -> None:
        """Background task to handle incoming messages."""
        self.logger.info("message_handler_started", agent_id=self.agent_id)

        try:
            while self._status == AgentStatus.RUNNING:
                try:
                    # Receive message with timeout to allow for status checks
                    message = await self.transport.receive(self.agent_id, timeout=1.0)

                    # Handle based on message type
                    if message.message_type == MessageType.HANDSHAKE_REQUEST:
                        await self._handle_handshake_request(HandshakeRequest(**message.model_dump()))

                    elif message.message_type == MessageType.REQUEST:
                        await self._handle_tool_request(RequestMessage(**message.model_dump()))

                    elif message.message_type == MessageType.RESPONSE:
                        await self._handle_tool_response(ResponseMessage(**message.model_dump()))

                    elif message.message_type == MessageType.NOTIFICATION:
                        await self._handle_notification(message)

                    elif message.message_type == MessageType.ERROR:
                        await self._handle_error(message)

                except TimeoutError:
                    # Normal - no messages available
                    continue
                except Exception as e:
                    self.logger.error(
                        "message_handler_error",
                        error=str(e),
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            self.logger.info("message_handler_cancelled", agent_id=self.agent_id)
            raise

        self.logger.info("message_handler_stopped", agent_id=self.agent_id)

    async def _handle_handshake_request(self, request: HandshakeRequest) -> None:
        """Handle incoming handshake request.

        Args:
            request: Handshake request message
        """
        self.logger.info(
            "handshake_request_received",
            sender_id=request.sender_id,
            sender_name=request.payload.agent_name,
        )

        # Store connection
        self._connected_agents[request.sender_id] = request.payload

        # Create our capabilities
        tools = await self.mcp.get_tools()
        capabilities = AgentCapabilities(
            agent_id=self.agent_id,
            agent_name=self.name,
            agent_role=self.role,
            tools=list(tools.keys()),
            version="0.1.0",
        )

        # Create response
        response = MCPBridgeProtocol.create_handshake_response(
            sender_id=self.agent_id,
            receiver_id=request.sender_id,
            capabilities=capabilities,
            correlation_id=request.message_id,
            accepted=True,
        )

        # Send response
        await self.transport.send(response)

        self.logger.info(
            "handshake_response_sent",
            sender_id=request.sender_id,
            accepted=True,
        )

    async def _handle_tool_request(self, request: RequestMessage) -> None:
        """Handle incoming tool invocation request.

        Args:
            request: Tool request message
        """
        start_time = time.time()
        tool_name = request.payload.tool_name

        self.logger.info(
            "tool_request_received",
            sender_id=request.sender_id,
            tool_name=tool_name,
            message_id=request.message_id,
        )

        try:
            # Get tool
            tools = await self.mcp.get_tools()

            if tool_name not in tools:
                # Tool not found
                response = MCPBridgeProtocol.create_response(
                    sender_id=self.agent_id,
                    receiver_id=request.sender_id,
                    correlation_id=request.message_id,
                    tool_response=ToolResponse(
                        success=False,
                        error=f"Tool '{tool_name}' not found",
                        execution_time=time.time() - start_time,
                    ),
                )
            else:
                # Invoke tool
                tool = tools[tool_name]
                # FastMCP tools have a callable interface - extract the actual function
                if hasattr(tool, 'fn'):
                    tool_fn = tool.fn
                elif callable(tool):
                    tool_fn = tool
                else:
                    raise RuntimeError(f"Tool '{tool_name}' is not callable")

                result = await tool_fn(**request.payload.arguments)

                # Create success response
                response = MCPBridgeProtocol.create_response(
                    sender_id=self.agent_id,
                    receiver_id=request.sender_id,
                    correlation_id=request.message_id,
                    tool_response=ToolResponse(
                        success=True,
                        result=result,
                        execution_time=time.time() - start_time,
                    ),
                )

            # Send response
            await self.transport.send(response)

            self.logger.info(
                "tool_response_sent",
                sender_id=request.sender_id,
                tool_name=tool_name,
                success=response.payload.success,
            )

        except Exception as e:
            # Send error response
            self.logger.error(
                "tool_execution_error",
                tool_name=tool_name,
                error=str(e),
                exc_info=True,
            )

            response = MCPBridgeProtocol.create_response(
                sender_id=self.agent_id,
                receiver_id=request.sender_id,
                correlation_id=request.message_id,
                tool_response=ToolResponse(
                    success=False,
                    error=str(e),
                    execution_time=time.time() - start_time,
                ),
            )
            await self.transport.send(response)

    async def _handle_tool_response(self, response: ResponseMessage) -> None:
        """Handle incoming tool response.

        Args:
            response: Tool response message
        """
        self.logger.info(
            "tool_response_received",
            sender_id=response.sender_id,
            correlation_id=response.correlation_id,
            success=response.payload.success,
        )

        # Resolve pending request future
        if response.correlation_id in self._pending_requests:
            future = self._pending_requests[response.correlation_id]
            if not future.done():
                future.set_result(response)

    async def _handle_notification(self, message: Any) -> None:
        """Handle incoming notification.

        Args:
            message: Notification message
        """
        self.logger.info(
            "notification_received",
            sender_id=message.sender_id,
            event_type=message.payload.get("event_type", "unknown"),
        )
        # TODO: Implement notification handling logic

    async def _handle_error(self, message: Any) -> None:
        """Handle incoming error message.

        Args:
            message: Error message
        """
        self.logger.error(
            "error_message_received",
            sender_id=message.sender_id,
            error_code=message.payload.get("error_code", "UNKNOWN"),
            error_message=message.payload.get("error_message", ""),
        )
        # TODO: Implement error handling logic

