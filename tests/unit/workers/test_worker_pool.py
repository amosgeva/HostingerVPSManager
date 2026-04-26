"""Tests for src.workers.WorkerPool.

These do exercise real Qt QThreads via APIWorker, but each worker
just runs a tiny pure-Python callable — no API calls, no network.
The `qtbot` fixture (pytest-qt) sets up a QApplication and provides
`waitSignal` / `waitUntil` helpers so we can synchronise without
sleeping.
"""

import pytest

from src.workers import APIWorker, WorkerPool

# --- helpers --------------------------------------------------------------


def _ok() -> int:
    return 42


def _boom() -> None:
    raise RuntimeError("boom")


# --- fixtures -------------------------------------------------------------


@pytest.fixture
def pool(qtbot) -> WorkerPool:  # noqa: ARG001 — qtbot ensures QApplication exists
    """A fresh WorkerPool per test. qtbot guarantees QApplication is alive."""
    return WorkerPool()


# --- happy path -----------------------------------------------------------


def test_submit_runs_the_callable_and_emits_finished(qtbot, pool: WorkerPool) -> None:
    worker = APIWorker(_ok)
    with qtbot.waitSignal(worker.finished, timeout=2000) as blocker:
        pool.submit(worker)
    assert blocker.args == [42]


def test_pool_retires_worker_after_finished(qtbot, pool: WorkerPool) -> None:
    worker = APIWorker(_ok)
    pool.submit(worker)
    # Wait for QThread's parameterless finished() signal — that fires
    # AFTER our custom APIWorker.finished(object) signal returns,
    # which is when the pool's _retire actually runs.
    qtbot.waitUntil(lambda: pool.active_count() == 0, timeout=2000)
    assert pool.active_count() == 0


def test_pool_retires_worker_after_error(qtbot, pool: WorkerPool) -> None:
    worker = APIWorker(_boom)
    with qtbot.waitSignal(worker.error, timeout=2000) as blocker:
        pool.submit(worker)
    assert "boom" in blocker.args[0]
    qtbot.waitUntil(lambda: pool.active_count() == 0, timeout=2000)


# --- multiple workers -----------------------------------------------------


def test_pool_handles_concurrent_workers(qtbot, pool: WorkerPool) -> None:
    workers = [APIWorker(_ok) for _ in range(5)]
    for w in workers:
        pool.submit(w)
    # active_count is zero once all five have run + retired.
    qtbot.waitUntil(lambda: pool.active_count() == 0, timeout=3000)


# --- shutdown -------------------------------------------------------------


def test_shutdown_with_no_active_workers_is_a_noop(pool: WorkerPool) -> None:
    pool.shutdown()
    assert pool.active_count() == 0


def test_shutdown_drains_in_flight_workers(qtbot, pool: WorkerPool) -> None:
    """Submit a worker, immediately call shutdown; pool ends up empty either
    way (the worker either finishes within the timeout or gets terminated)."""
    workers = [APIWorker(_ok) for _ in range(3)]
    for w in workers:
        pool.submit(w)
    pool.shutdown(timeout_ms=2000)
    assert pool.active_count() == 0
    # Process any deleteLater() events scheduled by shutdown.
    qtbot.wait(50)


def test_active_count_starts_at_zero(pool: WorkerPool) -> None:
    assert pool.active_count() == 0
