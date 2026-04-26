"""Dialog for adding an SSH public key."""

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
)


class SSHKeyDialog(QDialog):
    """Dialog for adding SSH public keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add SSH Public Key")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., My Laptop Key")
        layout.addRow("Name:", self.name_input)

        self.key_input = QTextEdit()
        self.key_input.setPlaceholderText("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAAB...")
        self.key_input.setMinimumHeight(100)
        layout.addRow("Public Key:", self.key_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_key_data(self) -> dict:
        return {"name": self.name_input.text().strip(), "key": self.key_input.toPlainText().strip()}
