"""Tests for settings configuration."""

import os
from collections.abc import Generator

import pytest
from pydantic import SecretStr

from mcp_swarm.config.settings import Settings


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Clean environment variables before and after test."""
    # Store original env
    original_env = dict(os.environ)

    # Clear relevant env vars
    env_vars = [
        "MCP_REGISTRY_URL",
        "AGENT_NAME",
        "AGENT_ROLE",
        "LOG_LEVEL",
        "LOG_FORMAT",
    ]
    for var in env_vars:
        os.environ.pop(var, None)

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_default_values(self, clean_env: None) -> None:
        """Test that Settings loads with sensible defaults."""
        # Act
        settings = Settings()

        # Assert
        assert settings.agent_name == "default-agent"
        assert settings.agent_role == "general"
        assert settings.agent_port == 8000
        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.service_name == "mcp-swarm"
        assert settings.mcp_registry_url == "https://registry.mcp.dev"
        assert settings.enable_metrics is True
        assert settings.state_backend == "memory"
        assert settings.tls_enabled is False

    def test_settings_from_environment(self, clean_env: None) -> None:
        """Test that Settings loads from environment variables."""
        # Arrange
        os.environ["AGENT_NAME"] = "test-agent"
        os.environ["AGENT_ROLE"] = "processor"
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["LOG_FORMAT"] = "pretty"

        # Act
        settings = Settings()

        # Assert
        assert settings.agent_name == "test-agent"
        assert settings.agent_role == "processor"
        assert settings.log_level == "DEBUG"
        assert settings.log_format == "pretty"

    def test_settings_case_insensitive(self, clean_env: None) -> None:
        """Test that Settings is case-insensitive."""
        # Arrange
        os.environ["agent_name"] = "lowercase-agent"
        os.environ["AGENT_ROLE"] = "uppercase-role"

        # Act
        settings = Settings()

        # Assert
        assert settings.agent_name == "lowercase-agent"
        assert settings.agent_role == "uppercase-role"

    def test_settings_secret_str_for_api_key(self, clean_env: None) -> None:
        """Test that API key is handled as SecretStr."""
        # Arrange
        os.environ["MCP_REGISTRY_API_KEY"] = "secret-key-123"

        # Act
        settings = Settings()

        # Assert
        assert isinstance(settings.mcp_registry_api_key, SecretStr)
        assert settings.mcp_registry_api_key.get_secret_value() == "secret-key-123"

    def test_settings_no_api_key_by_default(self, clean_env: None) -> None:
        """Test that API key is None when not provided."""
        # Act
        settings = Settings()

        # Assert
        assert settings.mcp_registry_api_key is None

    def test_settings_numeric_values(self, clean_env: None) -> None:
        """Test that numeric settings are properly typed."""
        # Arrange
        os.environ["AGENT_PORT"] = "9000"
        os.environ["METRICS_PORT"] = "9999"

        # Act
        settings = Settings()

        # Assert
        assert isinstance(settings.agent_port, int)
        assert settings.agent_port == 9000
        assert isinstance(settings.metrics_port, int)
        assert settings.metrics_port == 9999

    def test_settings_boolean_values(self, clean_env: None) -> None:
        """Test that boolean settings work correctly."""
        # Arrange
        os.environ["ENABLE_METRICS"] = "false"
        os.environ["TLS_ENABLED"] = "true"

        # Act
        settings = Settings()

        # Assert
        assert settings.enable_metrics is False
        assert settings.tls_enabled is True
