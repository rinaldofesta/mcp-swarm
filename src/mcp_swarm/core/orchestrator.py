"""Multi-agent orchestration."""

from typing import List
from mcp_swarm.core.agent import MCPAgent


class Orchestrator:
    """Orchestrates multiple MCP agents."""

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        self.agents: List[MCPAgent] = []

    async def register_agent(self, agent: MCPAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: The agent to register
        """
        # TODO: Implement agent registration
        self.agents.append(agent)

    async def coordinate(self, task: str) -> None:
        """Coordinate agents to complete a task.

        Args:
            task: The task to coordinate
        """
        # TODO: Implement coordination logic
        pass

