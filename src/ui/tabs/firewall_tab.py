"""Firewall tab — the passive view paired with `FirewallController`.

This widget is the template for the rest of the Phase 3 tab extractions:

  - Constructor takes the controller; that's the only dependency.
  - `__init__` connects every controller signal to a render method.
  - User actions (button clicks, combo changes) route to controller
    methods. Dialogs (`FirewallRuleDialog`, confirmation
    `QMessageBox`) live here because they're inherently UI concerns.
  - No business state on the widget — `current_firewall` lives on the
    controller. The widget just renders what arrives via signals.
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.api_client import Action, Firewall, FirewallRule
from ..dialogs import FirewallRuleDialog
from ..styles import CONFIRM_DELETE_TITLE, FIREWALL_SERVER_ERROR_MSG, REFRESH_BTN_TEXT

if TYPE_CHECKING:
    from ...controllers import FirewallController


class FirewallTab(QWidget):
    """Renders the firewall list, selected firewall's rules, and CRUD buttons."""

    def __init__(self, controller: "FirewallController", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._build_ui()
        self._wire_controller()

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Firewall selector + VM-bound actions
        fw_header = QHBoxLayout()
        fw_header.addWidget(QLabel("Firewall:"))

        self.firewall_combo = QComboBox()
        self.firewall_combo.setMinimumWidth(250)
        self.firewall_combo.currentIndexChanged.connect(self._on_combo_changed)
        fw_header.addWidget(self.firewall_combo)

        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setObjectName("success")
        self.activate_btn.clicked.connect(self._on_activate_clicked)
        fw_header.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("Deactivate")
        self.deactivate_btn.setObjectName("danger")
        self.deactivate_btn.clicked.connect(self._on_deactivate_clicked)
        fw_header.addWidget(self.deactivate_btn)

        self.sync_btn = QPushButton("Sync Rules")
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        fw_header.addWidget(self.sync_btn)

        fw_header.addStretch()
        layout.addLayout(fw_header)

        # Rules table
        rules_group = QGroupBox("Firewall Rules")
        rules_layout = QVBoxLayout(rules_group)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(5)
        self.rules_table.setHorizontalHeaderLabels(["ID", "Protocol", "Port", "Source", "Actions"])
        header = self.rules_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.rules_table.setColumnWidth(0, 80)
        self.rules_table.setColumnWidth(2, 80)
        self.rules_table.setColumnWidth(4, 160)
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.rules_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rules_layout.addWidget(self.rules_table)

        # Rule buttons
        rule_btns = QHBoxLayout()

        self.add_rule_btn = QPushButton("+ Add Rule")
        self.add_rule_btn.setObjectName("success")
        self.add_rule_btn.clicked.connect(self._on_add_rule_clicked)
        rule_btns.addWidget(self.add_rule_btn)

        self.refresh_btn = QPushButton(REFRESH_BTN_TEXT)
        self.refresh_btn.clicked.connect(self.controller.load_firewalls)
        rule_btns.addWidget(self.refresh_btn)

        rule_btns.addStretch()
        rules_layout.addLayout(rule_btns)

        layout.addWidget(rules_group)

    def _wire_controller(self) -> None:
        c = self.controller
        c.firewalls_loaded.connect(self._on_firewalls_loaded)
        c.rules_changed.connect(self._render_rules)
        c.rule_created.connect(self._on_rule_created)
        c.rule_updated.connect(self._on_rule_updated)
        c.rule_deleted.connect(self._on_rule_deleted)
        c.action_completed.connect(self._on_action_completed)
        c.error_occurred.connect(self._on_error)

    # --- controller -> UI -----------------------------------------------

    def _on_firewalls_loaded(self, firewalls: list[Firewall]) -> None:
        self.firewall_combo.blockSignals(True)
        self.firewall_combo.clear()
        self.firewall_combo.addItem("-- Select Firewall --", None)
        for fw in firewalls:
            status = "[Synced]" if fw.is_synced else "[Not Synced]"
            self.firewall_combo.addItem(f"{fw.name} {status} (ID: {fw.id})", fw.id)
        self.firewall_combo.blockSignals(False)

        # Auto-select the firewall associated with the current VM, if any.
        vm = self.controller.current_vm
        if vm is not None and vm.firewall_group_id is not None:
            for i in range(self.firewall_combo.count()):
                if self.firewall_combo.itemData(i) == vm.firewall_group_id:
                    self.firewall_combo.setCurrentIndex(i)
                    return

    def _render_rules(self, rules: list[FirewallRule]) -> None:
        self.rules_table.setRowCount(len(rules))
        for i, rule in enumerate(rules):
            self.rules_table.setItem(i, 0, QTableWidgetItem(str(rule.id)))
            self.rules_table.setItem(i, 1, QTableWidgetItem(rule.protocol.upper()))
            self.rules_table.setItem(i, 2, QTableWidgetItem(rule.port))

            source_text = rule.source
            if rule.source_detail:
                source_text += f" ({rule.source_detail})"
            self.rules_table.setItem(i, 3, QTableWidgetItem(source_text))

            self.rules_table.setCellWidget(i, 4, self._build_row_actions(rule))
            self.rules_table.setRowHeight(i, 40)

    def _build_row_actions(self, rule: FirewallRule) -> QWidget:
        actions_widget = QWidget()
        actions_widget.setStyleSheet("background: transparent;")
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 2, 2, 2)
        actions_layout.setSpacing(4)

        edit_btn = QPushButton("Edit")
        edit_btn.setFixedSize(70, 30)
        edit_btn.setStyleSheet(_EDIT_BTN_STYLE)
        edit_btn.clicked.connect(lambda _checked, r=rule: self._on_edit_rule_clicked(r))
        actions_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(70, 30)
        delete_btn.setStyleSheet(_DELETE_BTN_STYLE)
        delete_btn.clicked.connect(lambda _checked, r=rule: self._on_delete_rule_clicked(r))
        actions_layout.addWidget(delete_btn)

        return actions_widget

    def _on_rule_created(self, rule: FirewallRule) -> None:
        QMessageBox.information(self, "Success", f"Firewall rule created (ID: {rule.id})")

    def _on_rule_updated(self, _rule: FirewallRule) -> None:
        QMessageBox.information(self, "Success", "Firewall rule updated")

    def _on_rule_deleted(self) -> None:
        QMessageBox.information(self, "Success", "Firewall rule deleted")

    def _on_action_completed(self, action_name: str, action: Action) -> None:
        QMessageBox.information(
            self,
            "Action Started",
            f"Firewall {action_name.lower()} has been initiated.\nAction ID: {action.id}",
        )
        # Refresh after a short delay so the API state catches up.
        QTimer.singleShot(2000, self.controller.load_firewalls)

    def _on_error(self, message: str) -> None:
        QMessageBox.warning(self, "Error", message)

    # --- UI -> controller -----------------------------------------------

    def _on_combo_changed(self, index: int) -> None:
        self.controller.select_firewall(self.firewall_combo.itemData(index))

    def _on_add_rule_clicked(self) -> None:
        if self.controller.current_firewall is None:
            QMessageBox.warning(self, "Error", "Please select a firewall first.")
            return
        dialog = FirewallRuleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_rule_data()
            self.controller.create_rule(
                data["protocol"], data["port"], data["source"], data["source_detail"]
            )

    def _on_edit_rule_clicked(self, rule: FirewallRule) -> None:
        dialog = FirewallRuleDialog(self, rule)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_rule_data()
            self.controller.update_rule(
                rule.id, data["protocol"], data["port"], data["source"], data["source_detail"]
            )

    def _on_delete_rule_clicked(self, rule: FirewallRule) -> None:
        reply = QMessageBox.question(
            self,
            CONFIRM_DELETE_TITLE,
            f"Are you sure you want to delete this rule?\n"
            f"Protocol: {rule.protocol}, Port: {rule.port}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.delete_rule(rule.id)

    def _on_activate_clicked(self) -> None:
        if not self._require_vm_and_firewall():
            return
        reply = QMessageBox.question(
            self,
            "Confirm Activation",
            f"Activate firewall '{self.controller.current_firewall.name}' "
            f"for {self.controller.current_vm.hostname}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.activate()

    def _on_deactivate_clicked(self) -> None:
        if not self._require_vm_and_firewall():
            return
        reply = QMessageBox.question(
            self,
            "Confirm Deactivation",
            f"Deactivate firewall for {self.controller.current_vm.hostname}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.deactivate()

    def _on_sync_clicked(self) -> None:
        if not self._require_vm_and_firewall():
            return
        self.controller.sync()

    def _require_vm_and_firewall(self) -> bool:
        if self.controller.current_firewall is None or self.controller.current_vm is None:
            QMessageBox.warning(self, "Error", FIREWALL_SERVER_ERROR_MSG)
            return False
        return True


_EDIT_BTN_STYLE = """
    QPushButton {
        background-color: #0f3460;
        border: none;
        border-radius: 4px;
        color: #00d4ff;
        font-size: 11px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #00d4ff;
        color: #1a1a2e;
    }
"""


_DELETE_BTN_STYLE = """
    QPushButton {
        background-color: #e94560;
        border: none;
        border-radius: 4px;
        color: white;
        font-size: 11px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #ff6b6b;
    }
"""
