"""Pytest configuration and shared fixtures."""

import pytest
from typing import AsyncGenerator

# Add any shared fixtures here


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

