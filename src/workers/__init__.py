"""Background-thread plumbing.

`APIWorker` is the QThread subclass we run every Hostinger API call
on so the UI doesn't block. `WorkerPool` is the lifetime manager
that retires finished workers (preventing the leak that lived as
`MainWindow.workers.append(...)` until v1.1.0) and shuts the whole
fleet down cleanly on app exit.
"""

from .api_worker import APIWorker
from .worker_pool import WorkerPool

__all__ = ["APIWorker", "WorkerPool"]
