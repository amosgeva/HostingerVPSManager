"""Dialog for managing multiple Hostinger accounts."""

import os

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...app.resources import get_resource_path
from ...core.credentials import get_credential_manager
from ..styles import CONFIRM_DELETE_TITLE
from .add_account import AddAccountDialog


class AccountManagerDialog(QDialog):
    """Dialog for managing multiple accounts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Accounts")
        self.setMinimumSize(550, 450)
        self.cred_manager = get_credential_manager()
        self._set_window_icon()
        self.setup_ui()
        self.load_accounts()

    def _set_window_icon(self):
        """Set the window icon from assets."""
        icon_path = get_resource_path("assets/hostinger.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header with icon and title
        header_layout = QHBoxLayout()

        title_label = QLabel("🔐 Account Manager")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #00d4ff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Info label
        info_label = QLabel("Manage your Hostinger accounts. Each account has its own API token.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaaaaa; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Accounts table with better styling
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(2)
        self.accounts_table.setHorizontalHeaderLabels(["Account Name", "ID"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.accounts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.accounts_table.setColumnWidth(1, 120)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.accounts_table.setAlternatingRowColors(True)
        self.accounts_table.setStyleSheet("""
            QTableWidget {
                background-color: #16213e;
                border: 2px solid #0f3460;
                border-radius: 8px;
                gridline-color: #0f3460;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #0f3460;
            }
            QTableWidget::item:selected {
                background-color: #0f3460;
            }
            QTableWidget::item:alternate {
                background-color: #1a1a2e;
            }
        """)
        self.accounts_table.verticalHeader().setVisible(False)
        layout.addWidget(self.accounts_table)

        # Action buttons in a styled group
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.add_btn = QPushButton("➕ Add Account")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #00bf63;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00ff88;
                color: #1a1a2e;
            }
        """)
        self.add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #1a1a2e;
            }
        """)
        self.edit_btn.clicked.connect(self.edit_account)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_account)
        btn_layout.addWidget(self.delete_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Spacer
        layout.addStretch()

        # Close button at bottom
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                border: none;
                border-radius: 6px;
                padding: 12px 30px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00d4ff;
                color: #1a1a2e;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def load_accounts(self):
        accounts = self.cred_manager.get_accounts()
        self.accounts_table.setRowCount(len(accounts))

        for i, acc in enumerate(accounts):
            self.accounts_table.setItem(i, 0, QTableWidgetItem(acc.name))
            self.accounts_table.setItem(i, 1, QTableWidgetItem(acc.id))

    def add_account(self):
        dialog = AddAccountDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.get_name()
            token = dialog.get_token()

            if not name or not token:
                QMessageBox.warning(self, "Error", "Please enter both account name and API token.")
                return

            if self.cred_manager.add_account(name, token):
                self.load_accounts()
                QMessageBox.information(self, "Success", f"Account '{name}' added successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to add account.")

    def edit_account(self):
        row = self.accounts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select an account to edit.")
            return

        name = self.accounts_table.item(row, 0).text()
        account_id = self.accounts_table.item(row, 1).text()

        dialog = AddAccountDialog(self, edit_mode=True, account_name=name, account_id=account_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_name()
            new_token = dialog.get_token() or None  # None if empty

            if not new_name:
                QMessageBox.warning(self, "Error", "Please enter an account name.")
                return

            if self.cred_manager.update_account(account_id, name=new_name, token=new_token):
                self.load_accounts()
                QMessageBox.information(self, "Success", "Account updated successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to update account.")

    def delete_account(self):
        row = self.accounts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Error", "Please select an account to delete.")
            return

        name = self.accounts_table.item(row, 0).text()
        account_id = self.accounts_table.item(row, 1).text()

        reply = QMessageBox.question(
            self,
            CONFIRM_DELETE_TITLE,
            f"Are you sure you want to delete account '{name}'?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.cred_manager.delete_account(account_id):
                self.load_accounts()
                QMessageBox.information(self, "Success", "Account deleted successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete account.")
