"""Tests for src.core.formatting.datacenter."""

from src.core.api_client import DataCenter, VirtualMachine
from src.core.formatting import datacenter as dc_format

# --- helpers --------------------------------------------------------------


def _vm(*, data_center_id: int | None = None, template: object = None) -> VirtualMachine:
    """Construct a VirtualMachine with the fields these helpers actually read."""
    return VirtualMachine(
        id=1,
        hostname="vm-test",
        state="running",
        plan=None,
        cpus=1,
        memory=1024,
        disk=10240,
        bandwidth=100,
        ipv4=[],
        ipv6=None,
        firewall_group_id=None,
        template=template,
        created_at="2025-01-01T00:00:00Z",
        actions_lock="",
        data_center_id=data_center_id,
    )


def _dc(*, dc_id: int = 1, name=None, location=None, city=None) -> DataCenter:
    return DataCenter(id=dc_id, name=name, location=location, city=city, continent=None)


# --- get_os_name ----------------------------------------------------------


def test_get_os_name_returns_template_name() -> None:
    vm = _vm(template={"name": "Ubuntu 24.04", "version": "24.04"})
    assert dc_format.get_os_name(vm) == "Ubuntu 24.04"


def test_get_os_name_handles_missing_template() -> None:
    assert dc_format.get_os_name(_vm(template=None)) == "--"


def test_get_os_name_handles_template_dict_without_name() -> None:
    assert dc_format.get_os_name(_vm(template={"version": "24.04"})) == "--"


def test_get_os_name_handles_non_dict_template() -> None:
    # The API has been observed to occasionally return a string here.
    assert dc_format.get_os_name(_vm(template="legacy")) == "--"


# --- format_datacenter_display --------------------------------------------


def test_format_datacenter_display_with_city_and_location() -> None:
    dc = _dc(city="Amsterdam", location="nl")
    assert dc_format.format_datacenter_display(dc) == "Amsterdam, NL"


def test_format_datacenter_display_with_city_only() -> None:
    assert dc_format.format_datacenter_display(_dc(city="Amsterdam")) == "Amsterdam"


def test_format_datacenter_display_with_location_only() -> None:
    assert dc_format.format_datacenter_display(_dc(location="us")) == "US"


def test_format_datacenter_display_falls_back_to_name() -> None:
    dc = _dc(name="Some DC", city=None, location=None)
    assert dc_format.format_datacenter_display(dc) == "Some DC"


def test_format_datacenter_display_returns_dash_when_everything_is_none() -> None:
    assert dc_format.format_datacenter_display(_dc()) == "--"


# --- find_datacenter_by_id ------------------------------------------------


def test_find_datacenter_by_id_hit() -> None:
    dcs = [_dc(dc_id=1, city="A"), _dc(dc_id=2, city="B")]
    found = dc_format.find_datacenter_by_id(dcs, 2)
    assert found is not None
    assert found.id == 2
    assert found.city == "B"


def test_find_datacenter_by_id_miss() -> None:
    dcs = [_dc(dc_id=1)]
    assert dc_format.find_datacenter_by_id(dcs, 99) is None


def test_find_datacenter_by_id_empty_list() -> None:
    assert dc_format.find_datacenter_by_id([], 1) is None


# --- format_datacenter_for_vm (end-to-end) --------------------------------


def test_format_datacenter_for_vm_full_match() -> None:
    vm = _vm(data_center_id=42)
    dcs = [_dc(dc_id=42, city="Frankfurt", location="de")]
    assert dc_format.format_datacenter_for_vm(vm, dcs) == "Frankfurt, DE"


def test_format_datacenter_for_vm_no_id_returns_dash() -> None:
    vm = _vm(data_center_id=None)
    assert dc_format.format_datacenter_for_vm(vm, [_dc(dc_id=1)]) == "--"


def test_format_datacenter_for_vm_empty_list_falls_back_to_id() -> None:
    """The data centers list is fetched async; while it's still empty
    the UI should show *something* rather than a generic dash."""
    vm = _vm(data_center_id=42)
    assert dc_format.format_datacenter_for_vm(vm, []) == "42"


def test_format_datacenter_for_vm_id_not_in_list_falls_back_to_id() -> None:
    vm = _vm(data_center_id=42)
    dcs = [_dc(dc_id=1, city="Other")]
    assert dc_format.format_datacenter_for_vm(vm, dcs) == "42"
