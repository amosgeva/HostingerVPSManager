"""
Hostinger VPS Manager - Main Entry Point
A modern GUI application for managing Hostinger VPS instances.
"""

import logging
import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from . import __version__
from .main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    logger.info("Starting Hostinger VPS Manager v%s", __version__)

    app = QApplication(sys.argv)
    app.setApplicationName("Hostinger VPS Manager")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Hostinger VPS Manager")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create main window
    window = MainWindow()

    # Check if should start minimized. Only honour the setting when a system
    # tray is actually available — otherwise the window would hide with no
    # way for the user to bring it back.
    settings = QSettings("Hostinger", "VPSManager")
    start_minimized = settings.value("start_minimized", False, type=bool)

    if start_minimized and QSystemTrayIcon.isSystemTrayAvailable():
        logger.info("Starting minimized to system tray")
        window.hide()
    else:
        if start_minimized:
            logger.info("start_minimized requested but no system tray available; showing window")
        window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
