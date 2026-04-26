"""Dialog for adding or editing a Hostinger account / API token."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class AddAccountDialog(QDialog):
    """Dialog for adding a new account."""

    def __init__(self, parent=None, edit_mode=False, account_name="", account_id=None):
        super().__init__(parent)
        self.edit_mode = edit_mode
        self.account_id = account_id
        self.setWindowTitle("Edit Account" if edit_mode else "Add Account")
        self.setMinimumWidth(450)
        self.setup_ui(account_name)

    def setup_ui(self, account_name):
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Enter your Hostinger API token.\n"
            "You can generate one at: https://hpanel.hostinger.com/api-tokens"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., VPS 1, Production Server...")
        self.name_input.setText(account_name)
        form_layout.addRow("Account Name:", self.name_input)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste your API token here...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("API Token:", self.token_input)

        layout.addLayout(form_layout)

        self.show_token_btn = QPushButton("Show Token")
        self.show_token_btn.clicked.connect(self.toggle_token_visibility)
        layout.addWidget(self.show_token_btn)

        if self.edit_mode:
            note = QLabel("Leave token empty to keep the existing token.")
            note.setStyleSheet("color: #888;")
            layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("Hide Token")
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("Show Token")

    def get_name(self) -> str:
        return self.name_input.text().strip()

    def get_token(self) -> str:
        return self.token_input.text().strip()
