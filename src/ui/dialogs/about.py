"""About dialog — app name, version, license, and outbound links."""

import os
import platform

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ... import __version__
from ...app.resources import get_resource_path

GITHUB_URL = "https://github.com/amosgeva/HostingerVPSManager"
ISSUES_URL = "https://github.com/amosgeva/HostingerVPSManager/issues"
HOSTINGER_API_URL = "https://developers.hostinger.com/"


class AboutDialog(QDialog):
    """Modal "About" dialog with version, license, and external links."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Hostinger VPS Manager")
        self.setMinimumWidth(460)
        self._set_window_icon()
        self._build_ui()

    def _set_window_icon(self) -> None:
        icon_path = get_resource_path("assets/hostinger.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 20)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_description())
        layout.addWidget(self._build_metadata())
        layout.addWidget(self._build_links())
        layout.addWidget(self._build_environment())
        layout.addWidget(self._build_buttons())

    # --- sections -------------------------------------------------------

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_label = QLabel()
        icon_path = get_resource_path("assets/hostinger.png")
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
        icon_label.setFixedSize(64, 64)
        header.addWidget(icon_label)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)

        title = QLabel("Hostinger VPS Manager")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d4ff;")
        title_block.addWidget(title)

        version = QLabel(f"v{__version__}")
        version.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        title_block.addWidget(version)

        title_block.addStretch()
        header.addLayout(title_block)
        header.addStretch()
        return header

    def _build_description(self) -> QLabel:
        desc = QLabel(
            "Cross-platform desktop GUI for managing Hostinger VPS instances "
            "via the public Hostinger API."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cccccc;")
        return desc

    def _build_metadata(self) -> QLabel:
        meta = QLabel(
            "<table cellspacing='4'>"
            "<tr><td style='color:#888'>License:</td>"
            "<td style='color:#cccccc'>GPLv3</td></tr>"
            "<tr><td style='color:#888'>Author:</td>"
            "<td style='color:#cccccc'>Amos Geva</td></tr>"
            "</table>"
        )
        meta.setTextFormat(Qt.TextFormat.RichText)
        return meta

    def _build_links(self) -> QLabel:
        links = QLabel(
            f"<table cellspacing='4'>"
            f"<tr><td style='color:#888'>GitHub:</td>"
            f"<td><a href='{GITHUB_URL}' style='color:#00d4ff'>"
            f"amosgeva/HostingerVPSManager</a></td></tr>"
            f"<tr><td style='color:#888'>Issues:</td>"
            f"<td><a href='{ISSUES_URL}' style='color:#00d4ff'>Report a bug</a></td></tr>"
            f"<tr><td style='color:#888'>API docs:</td>"
            f"<td><a href='{HOSTINGER_API_URL}' style='color:#00d4ff'>"
            f"developers.hostinger.com</a></td></tr>"
            f"</table>"
        )
        links.setTextFormat(Qt.TextFormat.RichText)
        links.setOpenExternalLinks(True)
        return links

    def _build_environment(self) -> QLabel:
        """Compact environment line — useful when filing bug reports."""
        env = QLabel(
            f"<span style='color:#666; font-size:11px;'>"
            f"Python {platform.python_version()} · "
            f"{platform.system()} {platform.release()} · "
            f"{platform.machine()}"
            f"</span>"
        )
        env.setTextFormat(Qt.TextFormat.RichText)
        return env

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        return buttons
