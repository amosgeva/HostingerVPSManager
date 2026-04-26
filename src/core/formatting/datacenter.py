"""Formatting helpers for VirtualMachine + DataCenter values.

Pure functions over the dataclasses in `core.api_client`. No Qt
imports, no `self`, no global state. Designed for unit testing —
just construct the dataclasses and call.
"""

from collections.abc import Iterable

from ..api_client import DataCenter, VirtualMachine

UNAVAILABLE = "--"


def get_os_name(vm: VirtualMachine) -> str:
    """Return the OS name from a VM's template, or "--" if absent."""
    if not vm.template:
        return UNAVAILABLE
    if isinstance(vm.template, dict):
        return vm.template.get("name", UNAVAILABLE)
    return UNAVAILABLE


def find_datacenter_by_id(
    data_centers: Iterable[DataCenter],
    dc_id: int,
) -> DataCenter | None:
    """Linear scan; the caller decides whether to cache externally."""
    for dc in data_centers:
        if dc.id == dc_id:
            return dc
    return None


def format_datacenter_display(dc: DataCenter) -> str:
    """Render a DataCenter as `"<city>, <LOCATION>"` with sensible fallbacks.

    - If both city and location are present: `"Amsterdam, NL"`
    - If only one is present: just that one (location is upper-cased)
    - If neither: the data center's name, or "--"
    """
    parts = []
    if dc.city:
        parts.append(dc.city)
    if dc.location:
        parts.append(dc.location.upper())
    if parts:
        return ", ".join(parts)
    return dc.name if dc.name else UNAVAILABLE


def format_datacenter_for_vm(
    vm: VirtualMachine,
    data_centers: Iterable[DataCenter],
) -> str:
    """Display string for a VM's data center, given a list to look up in.

    Falls back to the raw id when the VM's `data_center_id` isn't in
    the supplied list (the UI shows *something* useful while the data
    center list is still loading).
    """
    if not vm.data_center_id:
        return UNAVAILABLE

    # An empty `data_centers` (e.g. list still loading) — show the id.
    dcs = list(data_centers)
    if not dcs:
        return str(vm.data_center_id)

    dc = find_datacenter_by_id(dcs, vm.data_center_id)
    if dc is None:
        return str(vm.data_center_id)
    return format_datacenter_display(dc)
