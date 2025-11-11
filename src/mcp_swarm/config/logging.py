"""Logging configuration for MCP-Swarm.

This module provides structured logging setup using structlog with support
for both JSON (production) and pretty-printed (development) formats.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    service_name: str = "mcp-swarm",
) -> None:
    """Configure structured logging with structlog.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" or "pretty")
        service_name: Service name to include in logs

    Raises:
        ValueError: If log_format is not "json" or "pretty"
    """
    if log_format not in ("json", "pretty"):
        raise ValueError(f"log_format must be 'json' or 'pretty', got: {log_format}")

    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Common processors for both formats
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add service name to all log entries
    structlog.contextvars.bind_contextvars(service=service_name)

    # Choose renderer based on format
    if log_format == "json":
        # Production: JSON format for machine parsing
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Pretty console output for humans
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.rich_traceback,
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Get a configured logger instance.

    Args:
        name: Optional logger name. If None, uses the calling module's name.

    Returns:
        A configured structlog logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("agent_started", agent_id="agent-1", role="processor")
    """
    return structlog.get_logger(name)
