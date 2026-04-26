"""Lifetime manager for `APIWorker` threads.

`MainWindow` used to do `self.workers.append(worker); worker.start()`
on every API call and never clean up; v1.1.0 added a minimal retire-on-
finish helper as a stop-gap. This module replaces that pattern with a
proper pool that:

  1. Retires workers automatically when their `finished` or `error`
     signal fires (drops the reference, calls `deleteLater()`).
  2. Provides cooperative shutdown: on app close we call
     `requestInterruption()` first and only fall back to `terminate()`
     for workers that don't exit within a timeout. `terminate()` skips
     `finally` blocks and is documented-dangerous, so we treat it as
     a last resort instead of the default.

The pool is intentionally not a `QObject` — it just brokers signal
connections between workers and itself. Tests can construct one
directly without a `QApplication` parent.
"""

import logging

from .api_worker import APIWorker

logger = logging.getLogger(__name__)


DEFAULT_SHUTDOWN_TIMEOUT_MS = 3000


class WorkerPool:
    """Owns a set of in-flight `APIWorker` threads.

    Typical use from a Qt widget:

        self.pool = WorkerPool()
        ...
        worker = APIWorker(api_call)
        worker.finished.connect(self._on_result)
        worker.error.connect(self._on_error)
        self.pool.submit(worker)        # starts the thread

        ...
        def closeEvent(self, event):
            self.pool.shutdown()
            event.accept()
    """

    def __init__(self) -> None:
        self._active: set[APIWorker] = set()

    def submit(self, worker: APIWorker) -> None:
        """Start `worker` and wire its retirement.

        Both `APIWorker.finished` and `APIWorker.error` signals are
        connected to a retire callback so the pool's reference is
        dropped no matter how the thread exits.
        """
        self._active.add(worker)
        # Use bound-method connections (not lambdas-over-closure) so the
        # connection can be reasoned about and explicitly disconnected
        # under test. `*_` swallows the payload (object for finished,
        # str for error).
        worker.finished.connect(lambda *_: self._retire(worker))
        worker.error.connect(lambda *_: self._retire(worker))
        worker.start()

    def _retire(self, worker: APIWorker) -> None:
        """Drop the pool's reference and schedule the worker for deletion.

        Idempotent: if both `finished` and `error` somehow fire (they
        shouldn't), the second call is a no-op.
        """
        self._active.discard(worker)
        worker.deleteLater()

    def shutdown(self, timeout_ms: int = DEFAULT_SHUTDOWN_TIMEOUT_MS) -> None:
        """Best-effort cooperative shutdown of every active worker.

        For each in-flight worker:
          1. `requestInterruption()` so the worker *could* notice (the
             signal is most useful when `run()` polls
             `isInterruptionRequested()`; today our workers don't, but
             keeping the call here means future cancellable workers
             will Just Work).
          2. `wait(timeout_ms)` for the thread to exit naturally.
          3. If it didn't, `terminate()` + `wait()` as a last resort.

        The pool is empty after this returns.
        """
        for worker in list(self._active):
            try:
                worker.requestInterruption()
                if not worker.wait(timeout_ms):
                    logger.warning(
                        "Worker %s did not exit within %dms; terminating",
                        worker,
                        timeout_ms,
                    )
                    worker.terminate()
                    worker.wait()
            except Exception:  # noqa: BLE001 — never raise from shutdown
                logger.exception("Error shutting down worker %s", worker)
            finally:
                self._active.discard(worker)
                worker.deleteLater()

    def active_count(self) -> int:
        """Number of workers still in flight. Intended for tests + diagnostics."""
        return len(self._active)
