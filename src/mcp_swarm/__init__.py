"""MCP-Swarm: Distributed AI Agent Orchestration via Model Context Protocol."""

__version__ = "0.1.0"

from mcp_swarm.config.logging import configure_logging, get_logger
from mcp_swarm.config.settings import Settings
from mcp_swarm.core.agent import MCPAgent
from mcp_swarm.core.orchestrator import Orchestrator

# Initialize logging with default settings on package import
# This can be reconfigured by users if needed
_settings = Settings()
configure_logging(
    log_level=_settings.log_level,
    log_format=_settings.log_format,
    service_name=_settings.service_name,
)

__all__ = [
    "MCPAgent",
    "Orchestrator",
    "Settings",
    "configure_logging",
    "get_logger",
    "__version__",
]

