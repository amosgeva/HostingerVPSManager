"""Dialog for adding / editing a firewall rule."""

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
)

from ...core.api_client import FirewallRule


class FirewallRuleDialog(QDialog):
    """Dialog for adding/editing firewall rules."""

    def __init__(self, parent=None, rule: FirewallRule = None):
        super().__init__(parent)
        self.rule = rule
        self.setWindowTitle("Edit Rule" if rule else "Add Firewall Rule")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)

        self.protocol_combo = QComboBox()
        # Hostinger API supports these protocol values
        self.protocol_combo.addItems(
            ["TCP", "UDP", "SSH", "HTTP", "HTTPS", "MYSQL", "FTP", "ICMP", "GRE"]
        )
        if self.rule:
            idx = self.protocol_combo.findText(self.rule.protocol.upper())
            if idx >= 0:
                self.protocol_combo.setCurrentIndex(idx)
        layout.addRow("Protocol:", self.protocol_combo)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("e.g., 80, 443, 8000-9000")
        if self.rule:
            self.port_input.setText(self.rule.port)
        layout.addRow("Port(s):", self.port_input)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["any", "custom"])
        if self.rule and self.rule.source != "any":
            self.source_combo.setCurrentText("custom")
        layout.addRow("Source:", self.source_combo)

        self.source_detail_input = QLineEdit()
        self.source_detail_input.setPlaceholderText("IP address or CIDR (e.g., 192.168.1.0/24)")
        if self.rule and self.rule.source_detail:
            self.source_detail_input.setText(self.rule.source_detail)
        layout.addRow("Source IP/CIDR:", self.source_detail_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_rule_data(self) -> dict:
        source = self.source_combo.currentText()
        return {
            "protocol": self.protocol_combo.currentText().upper(),
            "port": self.port_input.text().strip(),
            "source": source,
            "source_detail": self.source_detail_input.text().strip()
            if source == "custom"
            else None,
        }
