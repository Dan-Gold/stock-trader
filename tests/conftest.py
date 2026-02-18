"""Shared fixtures for unit tests."""

import pytest

from tests.in_memory.in_memory_backtest_repo import MemoryBacktestRepository
from tests.in_memory.in_memory_task_dispatcher import MemoryTaskDispatcher


@pytest.fixture()
def in_memory_repo() -> MemoryBacktestRepository:
    """Provide a fresh MemoryBacktestRepository for each test."""
    return MemoryBacktestRepository()


@pytest.fixture()
def in_memory_dispatcher() -> MemoryTaskDispatcher:
    """Provide a fresh MemoryTaskDispatcher for each test."""
    return MemoryTaskDispatcher()
