"""
Main window for the Hostinger VPS Manager application.
"""

import csv
import logging
import os
import platform
from datetime import datetime

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from .app.constants import DEFAULT_REFRESH_SECONDS
from .app.resources import get_resource_path
from .controllers import FirewallController
from .core.api_client import (
    Action,
    DataCenter,
    HostingerAPIClient,
    MalwareScanMetrics,
    PublicKey,
    Subscription,
    VirtualMachine,
)
from .core.credentials import get_credential_manager
from .core.formatting.datacenter import format_datacenter_for_vm, get_os_name
from .core.network.ip_detect import get_local_ip
from .ui.dialogs import (
    AboutDialog,
    AccountManagerDialog,
    AddAccountDialog,
    SettingsDialog,
    SSHKeyDialog,
)
from .ui.styles import (
    APP_NAME,
    COLOR_CYAN,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_WARNING,
    CONFIRM_DELETE_TITLE,
    DARK_THEME,
    FONT_SEGOE_UI,
    INFO_LABEL_STYLE,
    NO_SERVER_SELECTED_MSG,
    REFRESH_BTN_TEXT,
    STATUS_COLORS,
)
from .ui.tabs import FirewallTab
from .workers import APIWorker, WorkerPool

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.api_client: HostingerAPIClient | None = None
        self.virtual_machines: list[VirtualMachine] = []
        self.current_vm: VirtualMachine | None = None
        self.data_centers: list[DataCenter] = []
        self.worker_pool = WorkerPool()
        self.current_account_id: str | None = None
        self.cred_manager = get_credential_manager()

        # Phase 3 controllers — feature-state lives here, MainWindow just
        # coordinates account / VM selection across them.
        self.firewall_controller = FirewallController(self.api_client, self.worker_pool, self)
        self.firewall_controller.error_occurred.connect(self.on_api_error)

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(DARK_THEME)
        self._set_window_icon()

        # Settings
        self.settings = QSettings("Hostinger", "VPSManager")
        self.previous_vm_states: dict = {}  # Track VM states for notifications

        self.setup_ui()
        self.setup_system_tray()
        self.setup_timers()
        self.update_client_info_bar()  # Show local computer info
        self.check_credentials()

    def _set_window_icon(self):
        """Set the window icon from assets."""
        icon_path = get_resource_path("assets/hostinger.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            self.app_icon = QIcon(icon_path)
        else:
            self.app_icon = QIcon()

    def setup_system_tray(self):
        """Set up the system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available")
            return

        self.tray_icon = QSystemTrayIcon(self.app_icon, self)
        self.tray_icon.setToolTip(APP_NAME)

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_and_activate)
        tray_menu.addAction(show_action)

        refresh_action = QAction("Refresh Data", self)
        refresh_action.triggered.connect(self.refresh_data)
        tray_menu.addAction(refresh_action)

        tray_menu.addSeparator()

        about_action = QAction("About...", self)
        about_action.triggered.connect(self.show_about)
        tray_menu.addAction(about_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_and_activate(self):
        """Show and bring window to front."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_activate()

    def quit_application(self):
        """Quit the application completely."""
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()

    def copy_to_clipboard(self, text: str, label_name: str = "IP"):
        """Copy text to clipboard and show brief notification."""
        if text and text != "--":
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.show_tray_notification("Copied", f"{label_name} copied to clipboard: {text}")

    def create_copy_button(self, get_text_func, label_name: str = "IP") -> QPushButton:
        """Create a small copy button that copies text to clipboard."""
        copy_btn = QPushButton("📋")
        copy_btn.setToolTip(f"Copy {label_name} to clipboard")
        copy_btn.setFixedSize(24, 24)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #0f3460;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #00d4ff;
            }
        """)
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(get_text_func(), label_name))
        return copy_btn

    def show_tray_notification(self, title: str, message: str):
        """Show a system tray notification."""
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                title, message, QSystemTrayIcon.MessageIcon.Information, 5000
            )

    def setup_ui(self):
        """Set up the main UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("title")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Account selector
        header_layout.addWidget(QLabel("Account:"))
        self.account_combo = QComboBox()
        self.account_combo.setMinimumWidth(200)
        self.account_combo.currentIndexChanged.connect(self.on_account_changed)
        header_layout.addWidget(self.account_combo)

        # Manage accounts button
        self.manage_accounts_btn = QPushButton("⚙")
        self.manage_accounts_btn.setToolTip("Manage Accounts")
        self.manage_accounts_btn.setFixedSize(40, 40)
        self.manage_accounts_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #1a1a2e;
            }
        """)
        self.manage_accounts_btn.clicked.connect(self.show_account_manager)
        header_layout.addWidget(self.manage_accounts_btn)

        # Separator
        header_layout.addWidget(QLabel("  |  "))

        # Server selector
        self.server_combo = QComboBox()
        self.server_combo.setMinimumWidth(300)
        self.server_combo.currentIndexChanged.connect(self.on_server_changed)
        header_layout.addWidget(QLabel("Server:"))
        header_layout.addWidget(self.server_combo)

        # Refresh button
        self.refresh_btn = QPushButton(REFRESH_BTN_TEXT)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(self.refresh_btn)

        # Settings button
        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(self.settings_btn)

        # About button
        self.about_btn = QPushButton("ℹ About")
        self.about_btn.setToolTip("About Hostinger VPS Manager")
        self.about_btn.clicked.connect(self.show_about)
        header_layout.addWidget(self.about_btn)

        main_layout.addLayout(header_layout)

        # Status bar
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(
            "background-color: #16213e; border-radius: 10px; padding: 10px;"
        )
        status_layout = QHBoxLayout(self.status_frame)

        self.status_label = QLabel("Status: --")
        self.status_label.setFont(QFont(FONT_SEGOE_UI, 14, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        self.ip_label = QLabel("IP: --")
        status_layout.addWidget(self.ip_label)

        self.vps_ip_copy_btn = self.create_copy_button(self.get_current_vps_ip, "VPS IP")
        status_layout.addWidget(self.vps_ip_copy_btn)

        self.plan_label = QLabel("Plan: --")
        status_layout.addWidget(self.plan_label)

        self.lock_label = QLabel("")
        status_layout.addWidget(self.lock_label)

        main_layout.addWidget(self.status_frame)

        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)  # stretch factor

        # Create tabs
        self.create_overview_tab()
        self.create_metrics_tab()
        self.create_logs_tab()
        self.create_firewall_tab()
        self.create_ssh_tab()
        self.create_malware_tab()

        # Client info bar at bottom
        self.create_client_info_bar()
        main_layout.addWidget(self.client_info_frame)

    def create_overview_tab(self):
        """Create the overview tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Server info group
        info_group = QGroupBox("Server Information")
        info_layout = QGridLayout(info_group)

        self.info_labels = {}
        info_fields = [
            ("Hostname:", "hostname"),
            ("OS:", "os"),
            ("CPUs:", "cpus"),
            ("Memory:", "memory"),
            ("Disk:", "disk"),
            ("Bandwidth:", "bandwidth"),
            ("Created:", "created"),
            ("Data Center:", "datacenter"),
        ]

        for i, (label, key) in enumerate(info_fields):
            row, col = divmod(i, 2)
            info_layout.addWidget(QLabel(label), row, col * 2)
            value_label = QLabel("--")
            value_label.setStyleSheet(COLOR_CYAN)
            self.info_labels[key] = value_label
            info_layout.addWidget(value_label, row, col * 2 + 1)

        layout.addWidget(info_group)

        # Subscription info group
        sub_group = QGroupBox("Subscription Information")
        sub_layout = QGridLayout(sub_group)

        self.sub_labels = {}
        sub_fields = [
            ("Plan:", "plan_name"),
            ("Status:", "status"),
            ("Billing Period:", "billing_period"),
            ("Price:", "price"),
            ("Auto-Renewal:", "auto_renewal"),
            ("Next Billing:", "next_billing"),
            ("Created:", "sub_created"),
            ("Expires:", "expires"),
        ]

        for i, (label, key) in enumerate(sub_fields):
            row, col = divmod(i, 2)
            sub_layout.addWidget(QLabel(label), row, col * 2)
            value_label = QLabel("--")
            value_label.setStyleSheet(COLOR_CYAN)
            self.sub_labels[key] = value_label
            sub_layout.addWidget(value_label, row, col * 2 + 1)

        layout.addWidget(sub_group)

        # Control buttons
        control_group = QGroupBox("Server Controls")
        control_layout = QHBoxLayout(control_group)

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setObjectName("success")
        self.start_btn.clicked.connect(self.start_server)
        control_layout.addWidget(self.start_btn)

        self.restart_btn = QPushButton("⟳ Restart")
        self.restart_btn.clicked.connect(self.restart_server)
        control_layout.addWidget(self.restart_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.clicked.connect(self.stop_server)
        control_layout.addWidget(self.stop_btn)

        control_layout.addStretch()

        layout.addWidget(control_group)
        layout.addStretch()

        self.tabs.addTab(tab, "Overview")

    def create_metrics_tab(self):
        """Create the metrics tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Metrics display
        metrics_group = QGroupBox("Resource Usage (Last 24 Hours)")
        metrics_layout = QGridLayout(metrics_group)

        self.metric_bars = {}
        metrics = [("CPU", "cpu"), ("Memory", "memory"), ("Disk", "disk"), ("Network", "network")]

        for i, (label, key) in enumerate(metrics):
            metrics_layout.addWidget(QLabel(f"{label}:"), i, 0)
            progress = QProgressBar()
            progress.setMinimum(0)
            progress.setMaximum(100)
            progress.setValue(0)
            progress.setFormat("%v%")
            self.metric_bars[key] = progress
            metrics_layout.addWidget(progress, i, 1)

            value_label = QLabel("--")
            value_label.setMinimumWidth(150)
            self.metric_bars[f"{key}_label"] = value_label
            metrics_layout.addWidget(value_label, i, 2)

        layout.addWidget(metrics_group)

        # Uptime
        uptime_group = QGroupBox("Uptime")
        uptime_layout = QHBoxLayout(uptime_group)
        self.uptime_label = QLabel("--")
        self.uptime_label.setFont(QFont(FONT_SEGOE_UI, 16, QFont.Weight.Bold))
        self.uptime_label.setStyleSheet(COLOR_CYAN)
        uptime_layout.addWidget(self.uptime_label)
        layout.addWidget(uptime_group)

        # Export button
        export_metrics_btn = QPushButton("📥 Export Metrics to CSV")
        export_metrics_btn.clicked.connect(self.export_metrics_to_csv)
        layout.addWidget(export_metrics_btn)

        layout.addStretch()
        self.tabs.addTab(tab, "Metrics")

    def create_logs_tab(self):
        """Create the logs tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Actions table
        logs_group = QGroupBox("Server Actions History")
        logs_layout = QVBoxLayout(logs_group)

        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(4)
        self.logs_table.setHorizontalHeaderLabels(["Action", "Status", "Started", "Updated"])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.logs_table.setAlternatingRowColors(True)
        self.logs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        logs_layout.addWidget(self.logs_table)

        # Buttons row
        btn_layout = QHBoxLayout()

        refresh_logs_btn = QPushButton("⟳ Refresh Logs")
        refresh_logs_btn.clicked.connect(self.load_actions)
        btn_layout.addWidget(refresh_logs_btn)

        export_logs_btn = QPushButton("📥 Export to CSV")
        export_logs_btn.clicked.connect(self.export_logs_to_csv)
        btn_layout.addWidget(export_logs_btn)

        btn_layout.addStretch()
        logs_layout.addLayout(btn_layout)

        layout.addWidget(logs_group)
        self.tabs.addTab(tab, "Logs")

    def create_firewall_tab(self):
        """Add the firewall tab — paired with `self.firewall_controller`."""
        self.firewall_tab = FirewallTab(self.firewall_controller, self)
        self.tabs.addTab(self.firewall_tab, "Firewall")

    def create_ssh_tab(self):
        """Create the SSH Keys tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # SSH Keys header
        ssh_header = QHBoxLayout()
        ssh_header.addWidget(QLabel("SSH Public Keys"))
        ssh_header.addStretch()
        layout.addLayout(ssh_header)

        # SSH Keys table
        keys_group = QGroupBox("Public Keys")
        keys_layout = QVBoxLayout(keys_group)

        self.ssh_keys_table = QTableWidget()
        self.ssh_keys_table.setColumnCount(4)
        self.ssh_keys_table.setHorizontalHeaderLabels(["ID", "Name", "Key", "Actions"])
        self.ssh_keys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.ssh_keys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.ssh_keys_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.ssh_keys_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.ssh_keys_table.setColumnWidth(0, 80)  # ID
        self.ssh_keys_table.setColumnWidth(1, 150)  # Name
        self.ssh_keys_table.setColumnWidth(3, 100)  # Actions
        self.ssh_keys_table.setAlternatingRowColors(True)
        self.ssh_keys_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ssh_keys_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        keys_layout.addWidget(self.ssh_keys_table)

        # SSH Key buttons
        key_btns = QHBoxLayout()

        self.add_ssh_key_btn = QPushButton("+ Add Key")
        self.add_ssh_key_btn.setObjectName("success")
        self.add_ssh_key_btn.clicked.connect(self.add_ssh_key)
        key_btns.addWidget(self.add_ssh_key_btn)

        self.refresh_ssh_keys_btn = QPushButton(REFRESH_BTN_TEXT)
        self.refresh_ssh_keys_btn.clicked.connect(self.load_ssh_keys)
        key_btns.addWidget(self.refresh_ssh_keys_btn)

        key_btns.addStretch()
        keys_layout.addLayout(key_btns)

        layout.addWidget(keys_group)
        self.tabs.addTab(tab, "SSH")

    def create_malware_tab(self):
        """Create the Malware Scanner (Monarx) tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Malware Scanner header
        malware_header = QHBoxLayout()
        malware_header.addWidget(QLabel("Monarx Malware Scanner"))
        malware_header.addStretch()
        layout.addLayout(malware_header)

        # Scanner status group
        status_group = QGroupBox("Scanner Status")
        status_layout = QGridLayout(status_group)

        # Status indicator
        status_layout.addWidget(QLabel("Status:"), 0, 0)
        self.malware_status_label = QLabel("--")
        self.malware_status_label.setFont(QFont(FONT_SEGOE_UI, 10, QFont.Weight.Bold))
        status_layout.addWidget(self.malware_status_label, 0, 1)

        # Last scan time
        status_layout.addWidget(QLabel("Last Scan Started:"), 1, 0)
        self.malware_scan_started_label = QLabel("--")
        status_layout.addWidget(self.malware_scan_started_label, 1, 1)

        status_layout.addWidget(QLabel("Last Scan Ended:"), 2, 0)
        self.malware_scan_ended_label = QLabel("--")
        status_layout.addWidget(self.malware_scan_ended_label, 2, 1)

        layout.addWidget(status_group)

        # Scan metrics group
        metrics_group = QGroupBox("Scan Metrics")
        metrics_layout = QGridLayout(metrics_group)

        # Scanned files
        metrics_layout.addWidget(QLabel("Files Scanned:"), 0, 0)
        self.malware_scanned_files_label = QLabel("--")
        self.malware_scanned_files_label.setFont(QFont(FONT_SEGOE_UI, 12, QFont.Weight.Bold))
        self.malware_scanned_files_label.setStyleSheet(COLOR_CYAN)
        metrics_layout.addWidget(self.malware_scanned_files_label, 0, 1)

        # Records found
        metrics_layout.addWidget(QLabel("Records Found:"), 1, 0)
        self.malware_records_label = QLabel("--")
        self.malware_records_label.setFont(QFont(FONT_SEGOE_UI, 12, QFont.Weight.Bold))
        metrics_layout.addWidget(self.malware_records_label, 1, 1)

        # Malicious files
        metrics_layout.addWidget(QLabel("Malicious Files:"), 2, 0)
        self.malware_malicious_label = QLabel("--")
        self.malware_malicious_label.setFont(QFont(FONT_SEGOE_UI, 12, QFont.Weight.Bold))
        metrics_layout.addWidget(self.malware_malicious_label, 2, 1)

        # Compromised files
        metrics_layout.addWidget(QLabel("Compromised Files:"), 3, 0)
        self.malware_compromised_label = QLabel("--")
        self.malware_compromised_label.setFont(QFont(FONT_SEGOE_UI, 12, QFont.Weight.Bold))
        metrics_layout.addWidget(self.malware_compromised_label, 3, 1)

        layout.addWidget(metrics_group)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.install_monarx_btn = QPushButton("🛡️ Install Monarx")
        self.install_monarx_btn.setObjectName("success")
        self.install_monarx_btn.clicked.connect(self.install_monarx)
        btn_layout.addWidget(self.install_monarx_btn)

        self.uninstall_monarx_btn = QPushButton("🗑️ Uninstall Monarx")
        self.uninstall_monarx_btn.setObjectName("danger")
        self.uninstall_monarx_btn.clicked.connect(self.uninstall_monarx)
        btn_layout.addWidget(self.uninstall_monarx_btn)

        self.refresh_malware_btn = QPushButton(REFRESH_BTN_TEXT)
        self.refresh_malware_btn.clicked.connect(self.load_malware_metrics)
        btn_layout.addWidget(self.refresh_malware_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.tabs.addTab(tab, "Malware")

    def create_client_info_bar(self):
        """Create the client info bar at the bottom."""
        self.client_info_frame = QFrame()
        self.client_info_frame.setStyleSheet(
            "background-color: #16213e; border-radius: 10px; padding: 8px;"
        )
        info_layout = QHBoxLayout(self.client_info_frame)
        info_layout.setContentsMargins(15, 5, 15, 5)

        # OS
        self.os_label = QLabel("OS: --")
        self.os_label.setStyleSheet(INFO_LABEL_STYLE)
        info_layout.addWidget(self.os_label)

        info_layout.addWidget(QLabel("|"))

        # CPU
        self.cpu_info_label = QLabel("CPU: --")
        self.cpu_info_label.setStyleSheet(INFO_LABEL_STYLE)
        info_layout.addWidget(self.cpu_info_label)

        info_layout.addWidget(QLabel("|"))

        # RAM
        self.ram_info_label = QLabel("RAM: --")
        self.ram_info_label.setStyleSheet(INFO_LABEL_STYLE)
        info_layout.addWidget(self.ram_info_label)

        info_layout.addWidget(QLabel("|"))

        # Public IP
        self.public_ip_label = QLabel("Public IP: --")
        self.public_ip_label.setStyleSheet(INFO_LABEL_STYLE)
        info_layout.addWidget(self.public_ip_label)

        self.public_ip_copy_btn = self.create_copy_button(self.get_public_ip_text, "Public IP")
        info_layout.addWidget(self.public_ip_copy_btn)

        info_layout.addWidget(QLabel("|"))

        # Private IP
        self.private_ip_label = QLabel("Private IP: --")
        self.private_ip_label.setStyleSheet(INFO_LABEL_STYLE)
        info_layout.addWidget(self.private_ip_label)

        self.private_ip_copy_btn = self.create_copy_button(self.get_private_ip_text, "Private IP")
        info_layout.addWidget(self.private_ip_copy_btn)

        info_layout.addStretch()

    def update_client_info_bar(self):
        """Update the client info bar with LOCAL computer information."""
        # Get local OS info
        os_info = f"{platform.system()} {platform.release()}"
        self.os_label.setText(f"OS: {os_info}")

        # Get local CPU info
        if HAS_PSUTIL:
            cpu_count = psutil.cpu_count(logical=True)
            self.cpu_info_label.setText(f"CPU: {cpu_count} cores")
        else:
            self.cpu_info_label.setText("CPU: --")

        # Get local RAM info
        if HAS_PSUTIL:
            ram_bytes = psutil.virtual_memory().total
            ram_gb = ram_bytes / (1024**3)
            self.ram_info_label.setText(f"RAM: {ram_gb:.1f} GB")
        else:
            self.ram_info_label.setText("RAM: --")

        # Get local private IP from Ethernet adapter (not VPN/Tailscale)
        private_ip = get_local_ip()
        self.private_ip_label.setText(f"Private IP: {private_ip}")

        # Get public IP (in background to avoid blocking UI)
        self.fetch_public_ip()

    def fetch_public_ip(self):
        """Fetch public IP address in background."""
        import requests

        def get_public_ip():
            try:
                response = requests.get("https://api.ipify.org?format=json", timeout=5)
                if response.status_code == 200:
                    return response.json().get("ip", "--")
            except Exception as e:  # noqa: B110
                logger.debug("Failed to get public IP: %s", e)
            return "--"

        worker = APIWorker(get_public_ip)
        worker.finished.connect(lambda ip: self.public_ip_label.setText(f"Public IP: {ip}"))
        worker.error.connect(lambda e: self.public_ip_label.setText("Public IP: --"))
        self.worker_pool.submit(worker)

    def get_current_vps_ip(self) -> str:
        """Get the current VPS IP address from the label."""
        text = self.ip_label.text()
        return text.replace("IP: ", "") if text else "--"

    def get_public_ip_text(self) -> str:
        """Get the public IP address from the label."""
        text = self.public_ip_label.text()
        return text.replace("Public IP: ", "") if text else "--"

    def get_private_ip_text(self) -> str:
        """Get the private IP address from the label."""
        text = self.private_ip_label.text()
        return text.replace("Private IP: ", "") if text else "--"

    def setup_timers(self):
        """Set up auto-refresh timers."""
        interval = self.settings.value("refresh_interval", DEFAULT_REFRESH_SECONDS, type=int) * 1000
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(interval)

    def load_accounts(self):
        """Load accounts into the account combo box."""
        accounts = self.cred_manager.get_accounts()
        self.account_combo.blockSignals(True)
        self.account_combo.clear()

        for acc in accounts:
            self.account_combo.addItem(acc.name, acc.id)

        self.account_combo.blockSignals(False)
        return accounts

    def check_credentials(self):
        """Check if API credentials are stored and load accounts."""
        accounts = self.load_accounts()

        if accounts:
            # Select first account by default
            self.current_account_id = accounts[0].id
            token = self.cred_manager.get_token(self.current_account_id)
            if token:
                self._set_api_client(HostingerAPIClient(token))
                self.refresh_data()
        else:
            self.prompt_for_account()

    def _set_api_client(self, api_client: HostingerAPIClient | None) -> None:
        """Update the API client and propagate to controllers."""
        self.api_client = api_client
        self.firewall_controller.set_api_client(api_client)

    def prompt_for_account(self):
        """Prompt user to add their first account."""
        QMessageBox.information(
            self,
            "Welcome",
            f"Welcome to {APP_NAME}!\n\nPlease add your first account to get started.",
        )
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            token = dialog.get_token()
            if name and token:
                account = self.cred_manager.add_account(name, token)
                if account:
                    self.load_accounts()
                    self.current_account_id = account.id
                    self._set_api_client(HostingerAPIClient(token))
                    self.refresh_data()
                else:
                    QMessageBox.critical(self, "Error", "Failed to save account.")
                    self.prompt_for_account()
            else:
                QMessageBox.warning(self, "Error", "Please enter both account name and API token.")
                self.prompt_for_account()
        else:
            QMessageBox.information(self, "Info", "An account is required to use this application.")

    def on_account_changed(self, index: int):
        """Handle account selection change."""
        if index < 0:
            return

        account_id = self.account_combo.itemData(index)
        if account_id and account_id != self.current_account_id:
            self.current_account_id = account_id
            token = self.cred_manager.get_token(account_id)
            if token:
                self._set_api_client(HostingerAPIClient(token))
                self.virtual_machines = []
                self.current_vm = None
                self.firewall_controller.set_current_vm(None)
                self.server_combo.clear()
                self.refresh_data()
            else:
                QMessageBox.warning(self, "Error", "Could not retrieve token for this account.")

    def show_account_manager(self):
        """Show the account manager dialog."""
        dialog = AccountManagerDialog(self)
        dialog.exec()
        # Reload accounts after dialog closes
        current_idx = self.account_combo.currentIndex()
        accounts = self.load_accounts()

        if not accounts:
            self.prompt_for_account()
        elif current_idx < self.account_combo.count():
            self.account_combo.setCurrentIndex(current_idx)

    def show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply new refresh interval
            new_interval = (
                self.settings.value("refresh_interval", DEFAULT_REFRESH_SECONDS, type=int) * 1000
            )
            self.refresh_timer.setInterval(new_interval)

    def show_about(self):
        """Show the About dialog (version, license, GitHub links)."""
        AboutDialog(self).exec()

    def refresh_data(self):
        """Refresh all data from API."""
        if not self.api_client:
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("Loading...")

        worker = APIWorker(self.api_client.get_virtual_machines)
        worker.finished.connect(self.on_vms_loaded)
        worker.error.connect(self.on_api_error)
        self.worker_pool.submit(worker)

        # Also load SSH keys
        self.load_ssh_keys()

    def auto_refresh(self):
        """Auto-refresh current VM data."""
        if self.current_vm and self.api_client:
            self.load_vm_details(self.current_vm.id)
            self.load_metrics()

    def on_vms_loaded(self, vms: list[VirtualMachine]):
        """Handle VMs loaded."""
        # Check for state changes and notify
        self.check_vm_state_changes(vms)

        self.virtual_machines = vms
        self.server_combo.blockSignals(True)
        self.server_combo.clear()

        for vm in vms:
            self.server_combo.addItem(f"{vm.hostname} ({vm.plan})", vm.id)

        self.server_combo.blockSignals(False)

        if vms:
            self.server_combo.setCurrentIndex(0)
            self.on_server_changed(0)

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(REFRESH_BTN_TEXT)

        # Load firewalls
        self.firewall_controller.load_firewalls()

        # Load data centers (cache)
        self.load_data_centers()

    def load_data_centers(self):
        """Load data centers for caching."""
        if not self.api_client:
            return

        worker = APIWorker(self.api_client.get_data_centers)
        worker.finished.connect(self.on_data_centers_loaded)
        worker.error.connect(lambda e: logger.warning(f"Data centers error: {e}"))
        self.worker_pool.submit(worker)

    def on_data_centers_loaded(self, data_centers: list[DataCenter]):
        """Handle data centers loaded."""
        self.data_centers = data_centers
        logger.info(f"Loaded {len(data_centers)} data centers")
        # Update info display if a VM is selected
        if self.current_vm:
            self.update_info_display()

    def check_vm_state_changes(self, new_vms: list[VirtualMachine]):
        """Check for VM state changes and show notifications."""
        notifications_enabled = self.settings.value("notifications_enabled", True, type=bool)
        if not notifications_enabled:
            return

        for vm in new_vms:
            old_state = self.previous_vm_states.get(vm.id)
            if old_state and old_state != vm.state:
                self.show_tray_notification(
                    "Server Status Changed", f"{vm.hostname}: {old_state} → {vm.state}"
                )
            self.previous_vm_states[vm.id] = vm.state

    def on_server_changed(self, index: int):
        """Handle server selection change."""
        if index < 0 or index >= len(self.virtual_machines):
            return

        self.current_vm = self.virtual_machines[index]
        self.firewall_controller.set_current_vm(self.current_vm)
        self.update_status_display()
        self.update_info_display()
        self.load_metrics()
        self.load_actions()
        self.load_malware_metrics()
        self.load_subscriptions()

    def load_vm_details(self, vm_id: int):
        """Load detailed VM info."""
        if not self.api_client:
            return

        worker = APIWorker(self.api_client.get_virtual_machine, vm_id)
        worker.finished.connect(self.on_vm_details_loaded)
        worker.error.connect(self.on_api_error)
        self.worker_pool.submit(worker)

    def on_vm_details_loaded(self, vm: VirtualMachine):
        """Handle VM details loaded."""
        # Update current VM in list
        for i, v in enumerate(self.virtual_machines):
            if v.id == vm.id:
                self.virtual_machines[i] = vm
                if self.current_vm and self.current_vm.id == vm.id:
                    self.current_vm = vm
                    self.firewall_controller.set_current_vm(self.current_vm)
                break

        self.update_status_display()
        self.update_info_display()

    def update_status_display(self):
        """Update the status display."""
        if not self.current_vm:
            return

        state = self.current_vm.state
        color = STATUS_COLORS.get(state, "#888888")
        self.status_label.setText(f"Status: {state.upper()}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # IP address
        if self.current_vm.ipv4:
            ip = (
                self.current_vm.ipv4[0].get("address", "--")
                if isinstance(self.current_vm.ipv4[0], dict)
                else str(self.current_vm.ipv4[0])
            )
            self.ip_label.setText(f"IP: {ip}")
        else:
            self.ip_label.setText("IP: --")

        self.plan_label.setText(f"Plan: {self.current_vm.plan or '--'}")

        # Lock status
        if self.current_vm.actions_lock == "locked":
            self.lock_label.setText("🔒 Actions Locked")
            self.lock_label.setStyleSheet("color: #ffaa00;")
        else:
            self.lock_label.setText("")

        # Update button states
        is_running = state == "running"
        is_stopped = state == "stopped"
        is_locked = self.current_vm.actions_lock == "locked"

        self.start_btn.setEnabled(is_stopped and not is_locked)
        self.stop_btn.setEnabled(is_running and not is_locked)
        self.restart_btn.setEnabled(is_running and not is_locked)

    def update_info_display(self):
        """Update the info display."""
        if not self.current_vm:
            return

        vm = self.current_vm
        self.info_labels["hostname"].setText(vm.hostname)
        self.info_labels["os"].setText(get_os_name(vm))
        self.info_labels["cpus"].setText(str(vm.cpus))
        self.info_labels["memory"].setText(f"{vm.memory} MB ({vm.memory // 1024} GB)")
        self.info_labels["disk"].setText(f"{vm.disk} MB ({vm.disk // 1024} GB)")
        self.info_labels["bandwidth"].setText(f"{vm.bandwidth // 1024 // 1024} GB/month")
        self.info_labels["created"].setText(vm.created_at[:10] if vm.created_at else "--")
        self.info_labels["datacenter"].setText(format_datacenter_for_vm(vm, self.data_centers))

    def load_metrics(self):
        """Load metrics for current VM."""
        if not self.api_client or not self.current_vm:
            return

        worker = APIWorker(self.api_client.get_metrics, self.current_vm.id)
        worker.finished.connect(self.on_metrics_loaded)
        worker.error.connect(lambda e: logger.warning(f"Metrics error: {e}"))
        self.worker_pool.submit(worker)

    def on_metrics_loaded(self, metrics: dict):
        """Handle metrics loaded."""
        # Handle case where metrics might be wrapped in 'data' key
        if isinstance(metrics, dict) and "data" in metrics:
            metrics = metrics.get("data", {})

        # Log VM info for debugging
        if self.current_vm:
            logger.info(
                f"VM info: memory={self.current_vm.memory}MB, disk={self.current_vm.disk}MB"
            )

        # Process CPU (cpu_usage with usage dict {timestamp: value})
        cpu_data = metrics.get("cpu_usage", {}).get("usage", {})
        if cpu_data:
            values = list(cpu_data.values())
            avg_cpu = sum(values) / len(values)
            self.metric_bars["cpu"].setValue(int(avg_cpu))
            self.metric_bars["cpu_label"].setText(f"{avg_cpu:.1f}%")

        # Process Memory (ram_usage in bytes)
        ram_data = metrics.get("ram_usage", {}).get("usage", {})
        if ram_data and self.current_vm:
            values = list(ram_data.values())
            avg_ram_bytes = sum(values) / len(values)
            # Get total RAM from VM info (in MB, convert to bytes)
            total_ram_bytes = (self.current_vm.memory or 4096) * 1024 * 1024
            ram_percent = (avg_ram_bytes / total_ram_bytes) * 100
            self.metric_bars["memory"].setValue(int(ram_percent))
            avg_ram_gb = avg_ram_bytes / 1024 / 1024 / 1024
            total_ram_gb = (self.current_vm.memory or 4096) / 1024
            self.metric_bars["memory_label"].setText(
                f"{avg_ram_gb:.1f} / {total_ram_gb:.0f} GB ({ram_percent:.1f}%)"
            )
            logger.info(
                f"RAM: {avg_ram_bytes} bytes used, {total_ram_bytes} bytes total, {ram_percent:.1f}%"
            )

        # Process Disk (disk_space in bytes)
        disk_data = metrics.get("disk_space", {}).get("usage", {})
        if disk_data and self.current_vm:
            values = list(disk_data.values())
            avg_disk_bytes = sum(values) / len(values)
            # Get total disk from VM info (in MB, convert to bytes)
            total_disk_bytes = (self.current_vm.disk or 51200) * 1024 * 1024
            disk_percent = (avg_disk_bytes / total_disk_bytes) * 100
            self.metric_bars["disk"].setValue(int(disk_percent))
            avg_disk_gb = avg_disk_bytes / 1024 / 1024 / 1024
            total_disk_gb = (self.current_vm.disk or 51200) / 1024
            self.metric_bars["disk_label"].setText(
                f"{avg_disk_gb:.1f} / {total_disk_gb:.0f} GB ({disk_percent:.1f}%)"
            )
            logger.info(
                f"Disk: {avg_disk_bytes} bytes used, {total_disk_bytes} bytes total, {disk_percent:.1f}%"
            )

        # Process Network (incoming_traffic and outgoing_traffic in bytes)
        net_in_data = metrics.get("incoming_traffic", {}).get("usage", {})
        net_out_data = metrics.get("outgoing_traffic", {}).get("usage", {})
        if net_in_data or net_out_data:
            total_in = sum(net_in_data.values()) / 1024 / 1024  # MB
            total_out = sum(net_out_data.values()) / 1024 / 1024  # MB
            # Network bar shows relative usage (arbitrary scale)
            self.metric_bars["network"].setValue(min(100, int((total_in + total_out) / 100)))
            self.metric_bars["network_label"].setText(f"↓{total_in:.1f}MB ↑{total_out:.1f}MB")

        # Process Uptime (uptime in seconds)
        uptime_data = metrics.get("uptime", {}).get("usage", {})
        if uptime_data:
            # Get the latest uptime value (most recent timestamp)
            latest_uptime = max(uptime_data.values())
            days = int(latest_uptime // 86400)
            hours = int((latest_uptime % 86400) // 3600)
            mins = int((latest_uptime % 3600) // 60)
            self.uptime_label.setText(f"{days}d {hours}h {mins}m")

    def load_actions(self):
        """Load actions for current VM."""
        if not self.api_client or not self.current_vm:
            return

        worker = APIWorker(self.api_client.get_actions, self.current_vm.id)
        worker.finished.connect(self.on_actions_loaded)
        worker.error.connect(lambda e: logger.warning(f"Actions error: {e}"))
        self.worker_pool.submit(worker)

    def on_actions_loaded(self, actions: list[Action]):
        """Handle actions loaded."""
        self.logs_table.setRowCount(len(actions))

        for i, action in enumerate(actions):
            self.logs_table.setItem(i, 0, QTableWidgetItem(action.name))

            status_item = QTableWidgetItem(action.state)
            if action.state == "success":
                status_item.setForeground(Qt.GlobalColor.green)
            elif action.state == "error":
                status_item.setForeground(Qt.GlobalColor.red)
            self.logs_table.setItem(i, 1, status_item)

            self.logs_table.setItem(
                i, 2, QTableWidgetItem(action.created_at[:19] if action.created_at else "--")
            )
            self.logs_table.setItem(
                i, 3, QTableWidgetItem(action.updated_at[:19] if action.updated_at else "--")
            )

    # Server control methods
    def start_server(self):
        """Start the current server."""
        if not self.api_client or not self.current_vm:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Start",
            f"Are you sure you want to start {self.current_vm.hostname}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.execute_server_action("start", self.api_client.start_vm)

    def stop_server(self):
        """Stop the current server."""
        if not self.api_client or not self.current_vm:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Stop",
            f"Are you sure you want to stop {self.current_vm.hostname}?\nThis will shut down the server.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.execute_server_action("stop", self.api_client.stop_vm)

    def restart_server(self):
        """Restart the current server."""
        if not self.api_client or not self.current_vm:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Restart",
            f"Are you sure you want to restart {self.current_vm.hostname}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.execute_server_action("restart", self.api_client.restart_vm)

    def execute_server_action(self, action_name: str, action_func):
        """Execute a server action."""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.restart_btn.setEnabled(False)

        worker = APIWorker(action_func, self.current_vm.id)
        worker.finished.connect(lambda a: self.on_server_action_complete(action_name, a))
        worker.error.connect(self.on_api_error)
        self.worker_pool.submit(worker)

    def on_server_action_complete(self, action_name: str, action: Action):
        """Handle server action complete."""
        QMessageBox.information(
            self,
            "Action Started",
            f"{action_name.capitalize()} action has been initiated.\nAction ID: {action.id}",
        )
        # Refresh after a short delay
        QTimer.singleShot(2000, self.refresh_data)

    # SSH Keys methods
    def load_ssh_keys(self):
        """Load SSH public keys."""
        if not self.api_client:
            return

        worker = APIWorker(self.api_client.get_public_keys)
        worker.finished.connect(self.on_ssh_keys_loaded)
        worker.error.connect(lambda e: logger.warning(f"SSH keys error: {e}"))
        self.worker_pool.submit(worker)

    def on_ssh_keys_loaded(self, keys: list[PublicKey]):
        """Handle SSH keys loaded."""
        self.ssh_keys_table.setRowCount(len(keys))

        for i, key in enumerate(keys):
            self.ssh_keys_table.setRowHeight(i, 40)

            # ID
            id_item = QTableWidgetItem(str(key.id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ssh_keys_table.setItem(i, 0, id_item)

            # Name
            name_item = QTableWidgetItem(key.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ssh_keys_table.setItem(i, 1, name_item)

            # Key (truncated for display)
            key_display = key.key[:50] + "..." if len(key.key) > 50 else key.key
            key_item = QTableWidgetItem(key_display)
            key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            key_item.setToolTip(key.key)  # Full key on hover
            self.ssh_keys_table.setItem(i, 2, key_item)

            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(4)

            delete_btn = QPushButton("Delete")
            delete_btn.setFixedSize(70, 30)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4757;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6b6b;
                }
            """)
            delete_btn.clicked.connect(lambda checked, k=key: self.delete_ssh_key(k))
            actions_layout.addWidget(delete_btn)

            self.ssh_keys_table.setCellWidget(i, 3, actions_widget)

    def add_ssh_key(self):
        """Add a new SSH public key."""
        if not self.api_client:
            QMessageBox.warning(self, "Error", "No API client configured.")
            return

        dialog = SSHKeyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_key_data()
            if not data["name"] or not data["key"]:
                QMessageBox.warning(self, "Error", "Name and Key are required.")
                return

            worker = APIWorker(self.api_client.create_public_key, data["name"], data["key"])
            worker.finished.connect(self.on_ssh_key_created)
            worker.error.connect(self.on_api_error)
            self.worker_pool.submit(worker)

    def on_ssh_key_created(self, key: PublicKey):
        """Handle SSH key created."""
        QMessageBox.information(self, "Success", f"SSH key '{key.name}' created successfully.")
        self.load_ssh_keys()

    def delete_ssh_key(self, key: PublicKey):
        """Delete an SSH public key."""
        reply = QMessageBox.question(
            self,
            CONFIRM_DELETE_TITLE,
            f"Are you sure you want to delete the SSH key '{key.name}'?\n\n"
            "Note: This removes the key from your account but not from VMs it's attached to.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = APIWorker(self.api_client.delete_public_key, key.id)
            worker.finished.connect(lambda _: self.on_ssh_key_deleted(key.name))
            worker.error.connect(self.on_api_error)
            self.worker_pool.submit(worker)

    def on_ssh_key_deleted(self, key_name: str):
        """Handle SSH key deleted."""
        QMessageBox.information(self, "Success", f"SSH key '{key_name}' deleted.")
        self.load_ssh_keys()

    # Malware Scanner (Monarx) methods
    def load_malware_metrics(self):
        """Load malware scanner metrics for the current VM."""
        if not self.api_client or not self.current_vm:
            return

        worker = APIWorker(self.api_client.get_malware_metrics, self.current_vm.id)
        worker.finished.connect(self.on_malware_metrics_loaded)
        worker.error.connect(lambda e: logger.warning(f"Malware metrics error: {e}"))
        self.worker_pool.submit(worker)

    def on_malware_metrics_loaded(self, metrics: MalwareScanMetrics):
        """Handle malware metrics loaded."""
        if metrics is None:
            # Monarx not installed
            self.malware_status_label.setText("Not Installed")
            self.malware_status_label.setStyleSheet(COLOR_WARNING)
            self.malware_scan_started_label.setText("--")
            self.malware_scan_ended_label.setText("--")
            self.malware_scanned_files_label.setText("--")
            self.malware_records_label.setText("--")
            self.malware_malicious_label.setText("--")
            self.malware_compromised_label.setText("--")
            self.install_monarx_btn.setEnabled(True)
            self.uninstall_monarx_btn.setEnabled(False)
        else:
            # Monarx installed - show metrics
            self.malware_status_label.setText("Installed & Active")
            self.malware_status_label.setStyleSheet(COLOR_SUCCESS)

            # Format scan times
            if metrics.scan_started_at:
                self.malware_scan_started_label.setText(metrics.scan_started_at)
            else:
                self.malware_scan_started_label.setText("No scan yet")

            if metrics.scan_ended_at:
                self.malware_scan_ended_label.setText(metrics.scan_ended_at)
            else:
                self.malware_scan_ended_label.setText("Scan in progress or not started")

            # Display metrics
            self.malware_scanned_files_label.setText(f"{metrics.scanned_files:,}")
            self.malware_records_label.setText(str(metrics.records))

            # Color code malicious/compromised counts
            if metrics.malicious > 0:
                self.malware_malicious_label.setText(str(metrics.malicious))
                self.malware_malicious_label.setStyleSheet(COLOR_DANGER + " font-weight: bold;")
            else:
                self.malware_malicious_label.setText("0")
                self.malware_malicious_label.setStyleSheet(COLOR_SUCCESS)

            if metrics.compromised > 0:
                self.malware_compromised_label.setText(str(metrics.compromised))
                self.malware_compromised_label.setStyleSheet(COLOR_DANGER + " font-weight: bold;")
            else:
                self.malware_compromised_label.setText("0")
                self.malware_compromised_label.setStyleSheet(COLOR_SUCCESS)

            self.install_monarx_btn.setEnabled(False)
            self.uninstall_monarx_btn.setEnabled(True)

    def install_monarx(self):
        """Install Monarx malware scanner on the current VM."""
        if not self.api_client or not self.current_vm:
            QMessageBox.warning(self, "Error", NO_SERVER_SELECTED_MSG)
            return

        reply = QMessageBox.question(
            self,
            "Install Monarx",
            f"Install Monarx malware scanner on '{self.current_vm.hostname}'?\n\n"
            "This will enhance security by detecting and preventing malware.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = APIWorker(self.api_client.install_monarx, self.current_vm.id)
            worker.finished.connect(self.on_monarx_installed)
            worker.error.connect(self.on_api_error)
            self.worker_pool.submit(worker)

    def on_monarx_installed(self, action):
        """Handle Monarx installation initiated."""
        QMessageBox.information(
            self,
            "Monarx Installation",
            f"Monarx installation has been initiated.\nAction ID: {action.id}\n\n"
            "This may take a few minutes to complete.",
        )
        QTimer.singleShot(5000, self.load_malware_metrics)

    def uninstall_monarx(self):
        """Uninstall Monarx malware scanner from the current VM."""
        if not self.api_client or not self.current_vm:
            QMessageBox.warning(self, "Error", NO_SERVER_SELECTED_MSG)
            return

        reply = QMessageBox.question(
            self,
            "Uninstall Monarx",
            f"Uninstall Monarx malware scanner from '{self.current_vm.hostname}'?\n\n"
            "Warning: This will remove malware protection from this server.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = APIWorker(self.api_client.uninstall_monarx, self.current_vm.id)
            worker.finished.connect(self.on_monarx_uninstalled)
            worker.error.connect(self.on_api_error)
            self.worker_pool.submit(worker)

    def on_monarx_uninstalled(self, action):
        """Handle Monarx uninstallation initiated."""
        QMessageBox.information(
            self,
            "Monarx Uninstallation",
            f"Monarx uninstallation has been initiated.\nAction ID: {action.id}",
        )
        QTimer.singleShot(5000, self.load_malware_metrics)

    # Subscription methods
    def load_subscriptions(self):
        """Load subscription info for the current VM."""
        if not self.api_client or not self.current_vm:
            return

        # VMs have a subscription_id field
        if not hasattr(self.current_vm, "subscription_id") or not self.current_vm.subscription_id:
            self._clear_subscription_display()
            return

        worker = APIWorker(self.api_client.get_subscription_by_id, self.current_vm.subscription_id)
        worker.finished.connect(self.on_subscription_loaded)
        worker.error.connect(lambda e: logger.warning(f"Subscription load error: {e}"))
        self.worker_pool.submit(worker)

    def on_subscription_loaded(self, subscription: Subscription):
        """Handle subscription data loaded."""
        if subscription is None:
            self._clear_subscription_display()
            return

        # Plan name
        self.sub_labels["plan_name"].setText(subscription.name)

        # Status with color
        status = subscription.status
        self.sub_labels["status"].setText(status.upper())
        if status == "active":
            self.sub_labels["status"].setStyleSheet(COLOR_SUCCESS)
        elif status in ("cancelled", "paused"):
            self.sub_labels["status"].setStyleSheet(COLOR_DANGER)
        else:
            self.sub_labels["status"].setStyleSheet(COLOR_WARNING)

        # Billing period
        period_text = f"{subscription.billing_period} {subscription.billing_period_unit}"
        if subscription.billing_period > 1:
            period_text = f"{subscription.billing_period} {subscription.billing_period_unit}s"
        self.sub_labels["billing_period"].setText(period_text)

        # Price (convert cents to currency)
        price = subscription.renewal_price / 100
        self.sub_labels["price"].setText(f"{price:.2f} {subscription.currency_code}")

        # Auto renewal
        auto_text = "Yes" if subscription.is_auto_renewed else "No"
        self.sub_labels["auto_renewal"].setText(auto_text)
        if subscription.is_auto_renewed:
            self.sub_labels["auto_renewal"].setStyleSheet(COLOR_SUCCESS)
        else:
            self.sub_labels["auto_renewal"].setStyleSheet(COLOR_WARNING)

        # Next billing date
        if subscription.next_billing_at:
            next_billing = subscription.next_billing_at.split("T")[0]
            self.sub_labels["next_billing"].setText(next_billing)
        else:
            self.sub_labels["next_billing"].setText("--")

        # Created date
        if subscription.created_at:
            created = subscription.created_at.split("T")[0]
            self.sub_labels["sub_created"].setText(created)
        else:
            self.sub_labels["sub_created"].setText("--")

        # Expires date
        if subscription.expires_at:
            expires = subscription.expires_at.split("T")[0]
            self.sub_labels["expires"].setText(expires)
        else:
            self.sub_labels["expires"].setText("--")

    def _clear_subscription_display(self):
        """Clear subscription display when no subscription found."""
        for key in self.sub_labels:
            self.sub_labels[key].setText("--")
            self.sub_labels[key].setStyleSheet(COLOR_CYAN)

    def on_api_error(self, error_msg: str):
        """Handle API error."""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(REFRESH_BTN_TEXT)

        QMessageBox.critical(self, "API Error", f"An error occurred:\n{error_msg}")

        if "Unauthorized" in error_msg or "401" in error_msg:
            self.prompt_for_token()

    def closeEvent(self, event):
        """Handle window close - minimize to tray if enabled."""
        minimize_to_tray = self.settings.value("minimize_to_tray", True, type=bool)

        if minimize_to_tray and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.show_tray_notification(
                APP_NAME, "Application minimized to tray. Double-click to restore."
            )
        else:
            self.perform_cleanup()
            event.accept()

    def perform_cleanup(self):
        """Clean up resources before quitting."""
        self.worker_pool.shutdown()
        self.refresh_timer.stop()

        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()

    def export_logs_to_csv(self):
        """Export logs table to CSV file."""
        if self.logs_table.rowCount() == 0:
            QMessageBox.warning(self, "Export", "No logs to export.")
            return

        vm_name = self.current_vm.hostname if self.current_vm else "server"
        default_name = f"{vm_name}_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs to CSV", default_name, "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Header
                headers = []
                for col in range(self.logs_table.columnCount()):
                    headers.append(self.logs_table.horizontalHeaderItem(col).text())
                writer.writerow(headers)

                # Data
                for row in range(self.logs_table.rowCount()):
                    row_data = []
                    for col in range(self.logs_table.columnCount()):
                        item = self.logs_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            QMessageBox.information(self, "Export", f"Logs exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")

    def export_metrics_to_csv(self):
        """Export current metrics to CSV file."""
        if not self.current_vm:
            QMessageBox.warning(self, "Export", NO_SERVER_SELECTED_MSG)
            return

        vm_name = self.current_vm.hostname
        default_name = f"{vm_name}_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Metrics to CSV", default_name, "CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value", "Percentage"])

                for key in ["cpu", "memory", "disk", "network"]:
                    bar = self.metric_bars.get(key)
                    label = self.metric_bars.get(f"{key}_label")
                    if bar and label:
                        writer.writerow([key.capitalize(), label.text(), f"{bar.value()}%"])

                writer.writerow(["Uptime", self.uptime_label.text(), ""])

            QMessageBox.information(self, "Export", f"Metrics exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export:\n{e}")
