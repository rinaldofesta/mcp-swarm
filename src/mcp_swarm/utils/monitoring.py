"""Monitoring and observability utilities."""

from typing import Any

from ..config.logging import get_logger


class MonitoringService:
    """Monitoring service for agents.

    Provides centralized logging and metrics collection for agent operations.
    Uses structured logging to enable rich querying and analysis.

    Example:
        >>> monitor = MonitoringService(agent_id="agent-1")
        >>> monitor.log_event("task_started", task_id="task-123", duration_ms=42)
    """

    def __init__(self, agent_id: str) -> None:
        """Initialize the monitoring service.

        Args:
            agent_id: Unique identifier for the agent being monitored
        """
        self.agent_id = agent_id
        self.logger = get_logger(f"monitor.{agent_id}")

    def log_event(self, event_name: str, **kwargs: Any) -> None:
        """Log an event with structured data.

        Args:
            event_name: Name of the event (e.g., "agent_connected", "task_completed")
            **kwargs: Additional event data as key-value pairs

        Example:
            >>> monitor.log_event(
            ...     "message_sent",
            ...     target_agent="agent-2",
            ...     message_type="query",
            ...     size_bytes=1024
            ... )
        """
        self.logger.info(event_name, agent_id=self.agent_id, **kwargs)

