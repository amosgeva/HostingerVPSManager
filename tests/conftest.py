"""Shared pytest fixtures.

Phase-3 controllers are all headless-testable via `pytest-qt`'s
`qtbot.waitSignal` and a `MagicMock(spec=HostingerAPIClient)`. The
fake client honours the public surface of the real one so type-aware
tooling and `spec=...` strict mode catch typos.
"""

from unittest.mock import MagicMock

import pytest

from src.core.api_client import HostingerAPIClient
from src.workers import WorkerPool


@pytest.fixture
def fake_api_client() -> MagicMock:
    """A `MagicMock` spec'd to `HostingerAPIClient`'s public surface."""
    return MagicMock(spec=HostingerAPIClient)


@pytest.fixture
def worker_pool(qtbot) -> WorkerPool:  # noqa: ARG001 — qtbot makes a QApplication
    """A real `WorkerPool` — controllers want a live one for `submit()`."""
    return WorkerPool()
