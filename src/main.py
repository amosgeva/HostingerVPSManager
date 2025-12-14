"""
Hostinger VPS Manager - Main Entry Point
A modern GUI application for managing Hostinger VPS instances.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QFont

from .main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    logger.info("Starting Hostinger VPS Manager")

    app = QApplication(sys.argv)
    app.setApplicationName("Hostinger VPS Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Hostinger VPS Manager")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create main window
    window = MainWindow()

    # Check if should start minimized
    settings = QSettings("Hostinger", "VPSManager")
    start_minimized = settings.value("start_minimized", False, type=bool)

    if start_minimized:
        logger.info("Starting minimized to system tray")
        window.hide()
    else:
        window.show()

    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

