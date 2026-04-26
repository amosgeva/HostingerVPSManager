"""QThread wrapper that runs a callable off the UI thread."""

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.api_client import HostingerAPIError


class APIWorker(QThread):
    """Run `func(*args, **kwargs)` in a background thread.

    Emits `finished(result)` on success and `error(message)` on failure.
    These are *additional* signals on top of QThread's built-in
    parameterless `finished()` (which the WorkerPool uses for
    bookkeeping).
    """

    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except HostingerAPIError as e:
            self.error.emit(str(e.message))
        except Exception as e:  # noqa: BLE001 — surface any failure to the UI
            self.error.emit(str(e))
