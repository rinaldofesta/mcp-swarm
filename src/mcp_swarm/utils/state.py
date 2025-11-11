"""State management utilities."""

from dataclasses import dataclass, replace
from typing import FrozenSet


@dataclass(frozen=True)
class AgentState:
    """Immutable agent state representation."""

    agent_id: str
    status: str
    connected_agents: FrozenSet[str]

    def with_status(self, status: str) -> "AgentState":
        """Create a new state with updated status.

        Args:
            status: New status value

        Returns:
            New AgentState instance
        """
        return replace(self, status=status)


class StateManager:
    """Manages agent state synchronization."""

    def __init__(self) -> None:
        """Initialize the state manager."""
        self.states: dict[str, AgentState] = {}

    async def update_state(self, agent_id: str, state: AgentState) -> None:
        """Update agent state.

        Args:
            agent_id: Agent identifier
            state: New state
        """
        # TODO: Implement state update logic
        self.states[agent_id] = state

