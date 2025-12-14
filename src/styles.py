"""
Modern dark theme styles for the Hostinger VPS Manager.
"""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #eaeaea;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QLabel {
    color: #eaeaea;
}

QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: #00d4ff;
}

QLabel#subtitle {
    font-size: 14px;
    color: #888;
}

QLabel#status-running {
    color: #00ff88;
    font-weight: bold;
}

QLabel#status-stopped {
    color: #ff4444;
    font-weight: bold;
}

QLabel#status-other {
    color: #ffaa00;
    font-weight: bold;
}

QComboBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 8px 15px;
    color: #eaeaea;
    min-width: 200px;
}

QComboBox:hover {
    border-color: #00d4ff;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 2px solid #0f3460;
    selection-background-color: #0f3460;
    color: #eaeaea;
}

QPushButton {
    background-color: #0f3460;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: #eaeaea;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #00d4ff;
    color: #1a1a2e;
}

QPushButton:pressed {
    background-color: #00a8cc;
}

QPushButton:disabled {
    background-color: #333;
    color: #666;
}

QPushButton#danger {
    background-color: #e94560;
}

QPushButton#danger:hover {
    background-color: #ff6b6b;
}

QPushButton#success {
    background-color: #00bf63;
}

QPushButton#success:hover {
    background-color: #00ff88;
    color: #1a1a2e;
}

QGroupBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 10px;
    margin-top: 15px;
    padding: 15px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    color: #00d4ff;
}

QTableWidget {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    gridline-color: #0f3460;
    outline: none;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #0f3460;
    outline: none;
}

QTableWidget::item:selected {
    background-color: #0f3460;
    color: #00d4ff;
    outline: none;
}

QTableWidget::item:focus {
    background-color: #0f3460;
    color: #00d4ff;
    outline: none;
    border: none;
}

QTableWidget:focus {
    outline: none;
    border: 2px solid #0f3460;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #00d4ff;
    padding: 10px;
    border: none;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d4ff;
}

QTabWidget::pane {
    border: 2px solid #0f3460;
    border-radius: 10px;
    background-color: #16213e;
}

QTabBar::tab {
    background-color: #0f3460;
    color: #eaeaea;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

QTabBar::tab:selected {
    background-color: #00d4ff;
    color: #1a1a2e;
}

QTabBar::tab:hover:!selected {
    background-color: #16213e;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 8px;
    color: #eaeaea;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #00d4ff;
}

QProgressBar {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    text-align: center;
    color: #eaeaea;
}

QProgressBar::chunk {
    background-color: #00d4ff;
    border-radius: 6px;
}

QMessageBox {
    background-color: #1a1a2e;
}

QMessageBox QLabel {
    color: #eaeaea;
}

QDialog {
    background-color: #1a1a2e;
}

QSpinBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 8px;
    color: #eaeaea;
}

QSpinBox:focus {
    border-color: #00d4ff;
}
"""

# Status colors
STATUS_COLORS = {
    "running": "#00ff88",
    "starting": "#ffaa00",
    "stopping": "#ffaa00",
    "stopped": "#ff4444",
    "creating": "#00d4ff",
    "initial": "#888888",
    "error": "#ff4444",
    "suspending": "#ffaa00",
    "unsuspending": "#ffaa00",
    "suspended": "#ff6b6b",
    "destroying": "#ff4444",
    "destroyed": "#666666",
    "recreating": "#00d4ff",
    "restoring": "#00d4ff",
    "recovery": "#ffaa00",
    "stopping_recovery": "#ffaa00",
}

# UI Constants
APP_NAME = "Hostinger VPS Manager"
REFRESH_BTN_TEXT = "⟳ Refresh"
INFO_LABEL_STYLE = "color: #e0e0e0;"
FIREWALL_SERVER_ERROR_MSG = "Please select a firewall and server."
CONFIRM_DELETE_TITLE = "Confirm Delete"
NO_SERVER_SELECTED_MSG = "No server selected."
COLOR_SUCCESS = "color: #2ed573;"
COLOR_WARNING = "color: #ffa502;"
COLOR_DANGER = "color: #ff4757;"
COLOR_CYAN = "color: #00d4ff;"
FONT_SEGOE_UI = "Segoe UI"

