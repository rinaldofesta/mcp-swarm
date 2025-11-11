"""Configuration management."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # MCP Registry Configuration
    mcp_registry_url: str = "https://registry.mcp.dev"
    mcp_registry_api_key: SecretStr | None = None

    # Agent Configuration
    agent_name: str = "default-agent"
    agent_role: str = "general"
    agent_port: int = 8000

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # "json" for production, "pretty" for development
    service_name: str = "mcp-swarm"

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # State Management
    state_backend: str = "memory"
    state_persistence_path: str = "./state"

    # Security
    tls_enabled: bool = False
    tls_cert_path: str = ""
    tls_key_path: str = ""

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

