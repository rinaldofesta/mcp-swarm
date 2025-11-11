"""Abstract base agent."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent."""
        pass

    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Any:
        """Process a task.

        Args:
            context: Task context and parameters

        Returns:
            Processing result
        """
        pass

