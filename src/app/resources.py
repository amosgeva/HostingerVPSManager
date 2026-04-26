"""Resource-path helper for both `python run.py` and PyInstaller bundles."""

import os
import sys


def get_resource_path(relative_path: str) -> str:
    """Resolve a path inside the assets folder for dev and frozen runs.

    PyInstaller unpacks bundled data files into a temp directory exposed via
    `sys._MEIPASS`. In a normal `python run.py` checkout, paths are resolved
    relative to the project root (one level up from the `src/` package).
    """
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built executable.
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        # Running from source: src/app/resources.py -> src/ -> project root.
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)
