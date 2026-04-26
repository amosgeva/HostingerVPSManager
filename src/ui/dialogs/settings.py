"""Dialog for application settings (auto-refresh, tray, notifications)."""

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
)

from ...app.constants import DEFAULT_REFRESH_SECONDS, MAX_REFRESH_SECONDS, MIN_REFRESH_SECONDS


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, parent=None, settings: QSettings = None):
        super().__init__(parent)
        self.settings = settings or QSettings("Hostinger", "VPSManager")
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # General Settings Group
        general_group = QGroupBox("General")
        general_layout = QFormLayout(general_group)

        # Auto-refresh interval
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(MIN_REFRESH_SECONDS, MAX_REFRESH_SECONDS)
        self.refresh_interval_spin.setSuffix(" seconds")
        self.refresh_interval_spin.setToolTip("How often to auto-refresh server data")
        self.refresh_interval_spin.setStyleSheet("""
            QSpinBox {
                padding: 5px;
                padding-right: 25px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background-color: #16213e;
                border: 1px solid #0f3460;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #0f3460;
            }
            QSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #00d4ff;
                width: 0;
                height: 0;
            }
            QSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #00d4ff;
                width: 0;
                height: 0;
            }
        """)
        general_layout.addRow("Auto-refresh interval:", self.refresh_interval_spin)

        # Minimize to tray
        self.minimize_to_tray_check = QCheckBox("Minimize to system tray on close")
        self.minimize_to_tray_check.setToolTip("When closing, minimize to tray instead of quitting")
        general_layout.addRow(self.minimize_to_tray_check)

        # Start minimized
        self.start_minimized_check = QCheckBox("Start minimized")
        self.start_minimized_check.setToolTip("Start the application minimized to system tray")
        general_layout.addRow(self.start_minimized_check)

        layout.addWidget(general_group)

        # Notifications Group
        notif_group = QGroupBox("Notifications")
        notif_layout = QFormLayout(notif_group)

        self.notifications_check = QCheckBox("Enable status change notifications")
        self.notifications_check.setToolTip("Show tray notifications when server status changes")
        notif_layout.addRow(self.notifications_check)

        layout.addWidget(notif_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_settings(self):
        """Load current settings into UI."""
        self.refresh_interval_spin.setValue(
            self.settings.value("refresh_interval", DEFAULT_REFRESH_SECONDS, type=int)
        )
        self.minimize_to_tray_check.setChecked(
            self.settings.value("minimize_to_tray", True, type=bool)
        )
        self.start_minimized_check.setChecked(
            self.settings.value("start_minimized", False, type=bool)
        )
        self.notifications_check.setChecked(
            self.settings.value("notifications_enabled", True, type=bool)
        )

    def save_settings(self):
        """Save settings and close dialog."""
        self.settings.setValue("refresh_interval", self.refresh_interval_spin.value())
        self.settings.setValue("minimize_to_tray", self.minimize_to_tray_check.isChecked())
        self.settings.setValue("start_minimized", self.start_minimized_check.isChecked())
        self.settings.setValue("notifications_enabled", self.notifications_check.isChecked())
        self.accept()
