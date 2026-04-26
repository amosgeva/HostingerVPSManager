"""ViewModel for the Firewall tab.

This is the template controller for the Phase 3 refactor. The pattern:

  - `QObject` with `pyqtSignal`s on every state-change boundary.
  - Public methods take primitive args; signals carry primitive
    payloads. No Qt widgets imported.
  - Worker submissions go through an injected `WorkerPool`. Errors
    surface as `error_occurred(str)` so the view decides how to
    render them (QMessageBox today; could be a status bar or
    snackbar later).
  - Headless-testable: tests construct a controller with a
    `MagicMock(spec=HostingerAPIClient)` and use
    `qtbot.waitSignal(controller.firewalls_loaded, ...)`.

The remaining controllers (ssh, malware, subscription, metrics,
client_info, vps, accounts) will follow exactly this shape in step 6.
"""

import logging

from PyQt6.QtCore import QObject, pyqtSignal

from ..core.api_client import (
    Action,
    Firewall,
    FirewallRule,
    HostingerAPIClient,
    VirtualMachine,
)
from ..workers import APIWorker, WorkerPool

logger = logging.getLogger(__name__)


class FirewallController(QObject):
    """Owns firewall list, current selection, and CRUD on rules + VM actions."""

    # State signals
    firewalls_loaded = pyqtSignal(list)  # list[Firewall]
    firewall_selected = pyqtSignal(object)  # Firewall | None
    rules_changed = pyqtSignal(list)  # list[FirewallRule] for the selected firewall

    # Result signals
    rule_created = pyqtSignal(object)  # FirewallRule
    rule_updated = pyqtSignal(object)  # FirewallRule
    rule_deleted = pyqtSignal()
    action_completed = pyqtSignal(str, object)  # action_name, Action

    # Error channel
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        api_client: HostingerAPIClient | None,
        worker_pool: WorkerPool,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.worker_pool = worker_pool
        self.firewalls: list[Firewall] = []
        self.current_firewall: Firewall | None = None
        self.current_vm: VirtualMachine | None = None

    # --- dependency mutators ---------------------------------------------

    def set_api_client(self, api_client: HostingerAPIClient | None) -> None:
        """Swap in a new API client (e.g. on account switch)."""
        self.api_client = api_client
        # Stale state from the previous account would cause confusing UI.
        self.firewalls = []
        self.current_firewall = None
        self.firewalls_loaded.emit([])
        self.firewall_selected.emit(None)
        self.rules_changed.emit([])

    def set_current_vm(self, vm: VirtualMachine | None) -> None:
        """Track which VM is selected; required for activate/deactivate/sync."""
        self.current_vm = vm

    # --- queries ---------------------------------------------------------

    def load_firewalls(self) -> None:
        """Fetch the firewall list from the API; emits `firewalls_loaded`."""
        if self.api_client is None:
            return
        worker = APIWorker(self.api_client.get_firewalls)
        worker.finished.connect(self._on_firewalls_loaded)
        worker.error.connect(lambda e: logger.warning("Firewalls error: %s", e))
        self.worker_pool.submit(worker)

    def _on_firewalls_loaded(self, firewalls: list[Firewall]) -> None:
        self.firewalls = firewalls
        self.firewalls_loaded.emit(firewalls)
        # If a current firewall was selected, refresh its rules from the
        # new list so the UI sees up-to-date data.
        if self.current_firewall is not None:
            for fw in firewalls:
                if fw.id == self.current_firewall.id:
                    self.current_firewall = fw
                    self.rules_changed.emit(fw.rules)
                    return
            # Selection no longer in the list — clear it.
            self.current_firewall = None
            self.firewall_selected.emit(None)
            self.rules_changed.emit([])

    def select_firewall(self, firewall_id: int | None) -> None:
        """Set the current firewall by id. Emits `firewall_selected`/`rules_changed`."""
        if firewall_id is None:
            self.current_firewall = None
            self.firewall_selected.emit(None)
            self.rules_changed.emit([])
            return
        for fw in self.firewalls:
            if fw.id == firewall_id:
                self.current_firewall = fw
                self.firewall_selected.emit(fw)
                self.rules_changed.emit(fw.rules)
                return
        # Unknown id — treat as deselect.
        self.current_firewall = None
        self.firewall_selected.emit(None)
        self.rules_changed.emit([])

    # --- rule CRUD -------------------------------------------------------

    def create_rule(
        self,
        protocol: str,
        port: str,
        source: str,
        source_detail: str | None,
    ) -> None:
        if not self._require_firewall():
            return
        worker = APIWorker(
            self.api_client.create_firewall_rule,
            self.current_firewall.id,
            protocol,
            port,
            source,
            source_detail,
        )
        worker.finished.connect(self._on_rule_created)
        worker.error.connect(self.error_occurred.emit)
        self.worker_pool.submit(worker)

    def _on_rule_created(self, rule: FirewallRule) -> None:
        self.rule_created.emit(rule)
        # Refresh so the table re-renders with the new row.
        self.load_firewalls()

    def update_rule(
        self,
        rule_id: int,
        protocol: str,
        port: str,
        source: str,
        source_detail: str | None,
    ) -> None:
        if not self._require_firewall():
            return
        worker = APIWorker(
            self.api_client.update_firewall_rule,
            self.current_firewall.id,
            rule_id,
            protocol,
            port,
            source,
            source_detail,
        )
        worker.finished.connect(self._on_rule_updated)
        worker.error.connect(self.error_occurred.emit)
        self.worker_pool.submit(worker)

    def _on_rule_updated(self, rule: FirewallRule) -> None:
        self.rule_updated.emit(rule)
        self.load_firewalls()

    def delete_rule(self, rule_id: int) -> None:
        if not self._require_firewall():
            return
        worker = APIWorker(
            self.api_client.delete_firewall_rule,
            self.current_firewall.id,
            rule_id,
        )
        worker.finished.connect(lambda *_: self._on_rule_deleted())
        worker.error.connect(self.error_occurred.emit)
        self.worker_pool.submit(worker)

    def _on_rule_deleted(self) -> None:
        self.rule_deleted.emit()
        self.load_firewalls()

    # --- VM-bound actions ------------------------------------------------

    def activate(self) -> None:
        """Activate `current_firewall` on `current_vm`."""
        if not self._require_firewall_and_vm():
            return
        worker = APIWorker(
            self.api_client.activate_firewall,
            self.current_firewall.id,
            self.current_vm.id,
        )
        worker.finished.connect(lambda a: self.action_completed.emit("Activation", a))
        worker.error.connect(self.error_occurred.emit)
        self.worker_pool.submit(worker)

    def deactivate(self) -> None:
        """Deactivate firewall on `current_vm`."""
        if not self._require_firewall_and_vm():
            return
        worker = APIWorker(
            self.api_client.deactivate_firewall,
            self.current_firewall.id,
            self.current_vm.id,
        )
        worker.finished.connect(lambda a: self.action_completed.emit("Deactivation", a))
        worker.error.connect(self.error_occurred.emit)
        self.worker_pool.submit(worker)

    def sync(self) -> None:
        """Sync `current_firewall` rules to `current_vm`."""
        if not self._require_firewall_and_vm():
            return
        logger.info(
            "Initiating firewall sync: firewall=%s, vm=%s",
            self.current_firewall.id,
            self.current_vm.id,
        )
        worker = APIWorker(
            self.api_client.sync_firewall,
            self.current_firewall.id,
            self.current_vm.id,
        )
        worker.finished.connect(self._on_sync_complete)
        worker.error.connect(self._on_sync_error)
        self.worker_pool.submit(worker)

    def _on_sync_complete(self, action: Action) -> None:
        logger.info("Sync firewall completed: action_id=%s, state=%s", action.id, action.state)
        self.action_completed.emit("Sync", action)

    def _on_sync_error(self, error: str) -> None:
        logger.error("Sync firewall error: %s", error)
        self.error_occurred.emit(error)

    # --- preconditions ---------------------------------------------------

    def _require_firewall(self) -> bool:
        if self.api_client is None:
            self.error_occurred.emit("No API client configured.")
            return False
        if self.current_firewall is None:
            self.error_occurred.emit("Please select a firewall first.")
            return False
        return True

    def _require_firewall_and_vm(self) -> bool:
        if not self._require_firewall():
            return False
        if self.current_vm is None:
            self.error_occurred.emit("Please select a server first.")
            return False
        return True
