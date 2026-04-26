"""Headless tests for FirewallController.

This is the template — every other controller test (ssh, malware,
…) will follow this shape:

  - Construct controller with a `MagicMock(spec=HostingerAPIClient)`
    + a real `WorkerPool` (qtbot fixture in conftest.py).
  - Call public methods; assert via `qtbot.waitSignal(controller.foo)`.
  - Assert the controller actually called `api_client.bar(...)` with
    the right args.
"""

import pytest

from src.controllers import FirewallController
from src.core.api_client import (
    Action,
    DataCenter,  # noqa: F401 — imported for symmetry with vm fixture
    Firewall,
    FirewallRule,
    VirtualMachine,
)

# --- helpers --------------------------------------------------------------


def _firewall(*, fw_id: int = 1, name: str = "fw1", rules=None) -> Firewall:
    return Firewall(id=fw_id, name=name, is_synced=True, rules=rules or [])


def _rule(*, rule_id: int = 100, protocol: str = "tcp", port: str = "22") -> FirewallRule:
    return FirewallRule(id=rule_id, protocol=protocol, port=port, source="any", source_detail=None)


def _vm() -> VirtualMachine:
    return VirtualMachine(
        id=42,
        hostname="vm-test",
        state="running",
        plan=None,
        cpus=1,
        memory=1024,
        disk=10240,
        bandwidth=100,
        ipv4=[],
        ipv6=None,
        firewall_group_id=1,
        template=None,
        created_at="2025-01-01T00:00:00Z",
        actions_lock="",
    )


def _action(*, action_id: int = 999) -> Action:
    return Action(id=action_id, name="action", state="initiated", created_at="x", updated_at=None)


@pytest.fixture
def controller(fake_api_client, worker_pool):
    return FirewallController(api_client=fake_api_client, worker_pool=worker_pool)


# --- load_firewalls / select ----------------------------------------------


def test_load_firewalls_emits_firewalls_loaded(qtbot, controller, fake_api_client) -> None:
    fake_api_client.get_firewalls.return_value = [_firewall(fw_id=1), _firewall(fw_id=2)]
    with qtbot.waitSignal(controller.firewalls_loaded, timeout=2000) as blocker:
        controller.load_firewalls()
    assert [fw.id for fw in blocker.args[0]] == [1, 2]
    assert [fw.id for fw in controller.firewalls] == [1, 2]


def test_load_firewalls_does_nothing_when_api_client_is_none(controller) -> None:
    controller.api_client = None
    # Should not raise; should not emit (no waitSignal here on purpose).
    controller.load_firewalls()
    assert controller.firewalls == []


def test_select_firewall_emits_firewall_selected_and_rules_changed(qtbot, controller) -> None:
    rule = _rule()
    controller.firewalls = [_firewall(fw_id=7, rules=[rule])]
    with qtbot.waitSignals([controller.firewall_selected, controller.rules_changed], timeout=2000):
        controller.select_firewall(7)
    assert controller.current_firewall.id == 7


def test_select_firewall_with_none_clears_selection(qtbot, controller) -> None:
    controller.firewalls = [_firewall(fw_id=7)]
    controller.current_firewall = controller.firewalls[0]
    with qtbot.waitSignal(controller.firewall_selected, timeout=2000) as blocker:
        controller.select_firewall(None)
    assert blocker.args[0] is None
    assert controller.current_firewall is None


def test_select_firewall_with_unknown_id_clears_selection(qtbot, controller) -> None:
    controller.firewalls = [_firewall(fw_id=7)]
    with qtbot.waitSignal(controller.firewall_selected, timeout=2000) as blocker:
        controller.select_firewall(99)
    assert blocker.args[0] is None


# --- create_rule ----------------------------------------------------------


def test_create_rule_calls_api_with_correct_args(qtbot, controller, fake_api_client) -> None:
    fake_api_client.create_firewall_rule.return_value = _rule()
    fake_api_client.get_firewalls.return_value = []  # for the post-create reload
    controller.current_firewall = _firewall(fw_id=5)

    with qtbot.waitSignal(controller.rule_created, timeout=2000):
        controller.create_rule(protocol="TCP", port="80", source="any", source_detail=None)

    fake_api_client.create_firewall_rule.assert_called_once_with(5, "TCP", "80", "any", None)


def test_create_rule_without_firewall_emits_error(qtbot, controller, fake_api_client) -> None:
    with qtbot.waitSignal(controller.error_occurred, timeout=2000) as blocker:
        controller.create_rule("TCP", "80", "any", None)
    assert "select a firewall" in blocker.args[0].lower()
    fake_api_client.create_firewall_rule.assert_not_called()


# --- update_rule / delete_rule -------------------------------------------


def test_update_rule_calls_api_with_correct_args(qtbot, controller, fake_api_client) -> None:
    fake_api_client.update_firewall_rule.return_value = _rule(rule_id=100)
    fake_api_client.get_firewalls.return_value = []
    controller.current_firewall = _firewall(fw_id=5)

    with qtbot.waitSignal(controller.rule_updated, timeout=2000):
        controller.update_rule(100, "UDP", "53", "custom", "10.0.0.0/24")

    fake_api_client.update_firewall_rule.assert_called_once_with(
        5, 100, "UDP", "53", "custom", "10.0.0.0/24"
    )


def test_delete_rule_calls_api_and_emits(qtbot, controller, fake_api_client) -> None:
    fake_api_client.delete_firewall_rule.return_value = None
    fake_api_client.get_firewalls.return_value = []
    controller.current_firewall = _firewall(fw_id=5)

    with qtbot.waitSignal(controller.rule_deleted, timeout=2000):
        controller.delete_rule(100)

    fake_api_client.delete_firewall_rule.assert_called_once_with(5, 100)


# --- VM-bound actions -----------------------------------------------------


def test_activate_calls_api_when_vm_and_firewall_set(qtbot, controller, fake_api_client) -> None:
    fake_api_client.activate_firewall.return_value = _action()
    controller.current_firewall = _firewall(fw_id=5)
    controller.set_current_vm(_vm())

    with qtbot.waitSignal(controller.action_completed, timeout=2000) as blocker:
        controller.activate()

    fake_api_client.activate_firewall.assert_called_once_with(5, 42)
    assert blocker.args[0] == "Activation"
    assert blocker.args[1].id == 999


def test_activate_without_vm_emits_error(qtbot, controller, fake_api_client) -> None:
    controller.current_firewall = _firewall()
    controller.current_vm = None
    with qtbot.waitSignal(controller.error_occurred, timeout=2000) as blocker:
        controller.activate()
    assert "select a server" in blocker.args[0].lower()
    fake_api_client.activate_firewall.assert_not_called()


def test_sync_calls_api_when_vm_and_firewall_set(qtbot, controller, fake_api_client) -> None:
    fake_api_client.sync_firewall.return_value = _action()
    controller.current_firewall = _firewall(fw_id=5)
    controller.set_current_vm(_vm())

    with qtbot.waitSignal(controller.action_completed, timeout=2000) as blocker:
        controller.sync()

    fake_api_client.sync_firewall.assert_called_once_with(5, 42)
    assert blocker.args[0] == "Sync"


# --- account switch -------------------------------------------------------


def test_set_api_client_clears_state_and_emits(qtbot, controller, fake_api_client) -> None:
    controller.firewalls = [_firewall()]
    controller.current_firewall = controller.firewalls[0]

    with qtbot.waitSignals(
        [controller.firewalls_loaded, controller.firewall_selected, controller.rules_changed],
        timeout=2000,
    ):
        controller.set_api_client(fake_api_client)

    assert controller.firewalls == []
    assert controller.current_firewall is None
