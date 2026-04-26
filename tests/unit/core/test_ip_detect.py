"""Tests for src.core.network.ip_detect.

Pure functions, no Qt, no real network access. We fake
`psutil.net_if_addrs()` / `psutil.net_if_stats()` shapes with
`SimpleNamespace` so the tests are independent of psutil's exact
namedtuple internals.
"""

import socket
from types import SimpleNamespace

import pytest

from src.core.network import ip_detect

# --- helpers --------------------------------------------------------------


def _addr(family: int, address: str) -> SimpleNamespace:
    """Mimic `psutil._common.snicaddr` for the fields we read."""
    return SimpleNamespace(family=family, address=address)


def _stats(isup: bool = True) -> SimpleNamespace:
    """Mimic `psutil._common.snicstats` for the fields we read."""
    return SimpleNamespace(isup=isup)


# --- is_priority_interface ------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["ethernet", "ethernet 2", "eth0", "wi-fi", "wlan0", "en0", "en1"],
)
def test_is_priority_interface_matches_physical_nic_names(name: str) -> None:
    assert ip_detect.is_priority_interface(name) is True


@pytest.mark.parametrize("name", ["docker0", "tailscale0", "utun5", "lo"])
def test_is_priority_interface_does_not_match_virtual_names(name: str) -> None:
    # `lo` happens to contain neither priority nor exclude substrings;
    # it's filtered out by IP (127.*), not name.
    assert ip_detect.is_priority_interface(name) is False


# --- should_skip_interface ------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "tailscale0",
        "docker0",
        "vboxnet0",
        "vmware",
        "wsl",
        "tun0",
        "tap0",
        "br-1234abcd",
        "utun3",
        "awdl0",
        "vethernet (wsl)",
    ],
)
def test_should_skip_interface_matches_known_virtual(name: str) -> None:
    assert ip_detect.should_skip_interface(name) is True


@pytest.mark.parametrize("name", ["ethernet", "wi-fi", "en0", "wlan0"])
def test_should_skip_interface_keeps_real_nics(name: str) -> None:
    assert ip_detect.should_skip_interface(name) is False


# --- get_valid_ipv4 -------------------------------------------------------


def test_get_valid_ipv4_returns_first_routable() -> None:
    addrs = [
        _addr(socket.AF_INET6, "fe80::1"),
        _addr(socket.AF_INET, "192.168.1.20"),
        _addr(socket.AF_INET, "10.0.0.5"),
    ]
    assert ip_detect.get_valid_ipv4(addrs) == "192.168.1.20"


def test_get_valid_ipv4_skips_loopback_and_link_local() -> None:
    addrs = [
        _addr(socket.AF_INET, "127.0.0.1"),
        _addr(socket.AF_INET, "169.254.42.1"),
        _addr(socket.AF_INET, "10.0.0.5"),
    ]
    assert ip_detect.get_valid_ipv4(addrs) == "10.0.0.5"


def test_get_valid_ipv4_returns_none_when_no_ipv4() -> None:
    addrs = [_addr(socket.AF_INET6, "fe80::1")]
    assert ip_detect.get_valid_ipv4(addrs) is None


# --- find_best_ip ---------------------------------------------------------


def test_find_best_ip_prefers_priority_over_fallback() -> None:
    interfaces = {
        # Encountered first, no priority match -> fallback.
        "Some Adapter": [_addr(socket.AF_INET, "10.0.0.5")],
        # Priority match -> returned as best.
        "Ethernet": [_addr(socket.AF_INET, "192.168.1.20")],
    }
    best, fallback = ip_detect.find_best_ip(interfaces)
    assert best == "192.168.1.20"
    # The fallback we accumulated before the priority match is still reported.
    assert fallback == "10.0.0.5"


def test_find_best_ip_returns_fallback_when_no_priority_match() -> None:
    interfaces = {
        "Some Adapter": [_addr(socket.AF_INET, "10.0.0.5")],
    }
    best, fallback = ip_detect.find_best_ip(interfaces)
    assert best is None
    assert fallback == "10.0.0.5"


def test_find_best_ip_skips_excluded_interfaces() -> None:
    interfaces = {
        "tailscale0": [_addr(socket.AF_INET, "100.64.1.1")],
        "docker0": [_addr(socket.AF_INET, "172.17.0.1")],
        "Ethernet": [_addr(socket.AF_INET, "192.168.1.20")],
    }
    best, _ = ip_detect.find_best_ip(interfaces)
    assert best == "192.168.1.20"


def test_find_best_ip_skips_down_interfaces_when_stats_provided() -> None:
    interfaces = {
        # Looks priority but reports down — must be skipped.
        "Ethernet": [_addr(socket.AF_INET, "192.168.1.20")],
        # Lower-priority but up.
        "Some Adapter": [_addr(socket.AF_INET, "10.0.0.5")],
    }
    stats = {
        "Ethernet": _stats(isup=False),
        "Some Adapter": _stats(isup=True),
    }
    best, fallback = ip_detect.find_best_ip(interfaces, stats)
    assert best is None
    assert fallback == "10.0.0.5"


def test_find_best_ip_with_no_stats_falls_back_to_name_only_filter() -> None:
    """When stats=None we don't filter on isup; behaviour matches the
    pre-Phase-2 code."""
    interfaces = {
        "Ethernet": [_addr(socket.AF_INET, "192.168.1.20")],
    }
    best, _ = ip_detect.find_best_ip(interfaces, stats=None)
    assert best == "192.168.1.20"


def test_find_best_ip_returns_none_pair_when_nothing_usable() -> None:
    interfaces = {
        "tailscale0": [_addr(socket.AF_INET, "100.64.1.1")],  # excluded
        "Ethernet (down)": [_addr(socket.AF_INET, "127.0.0.1")],  # loopback IP
    }
    assert ip_detect.find_best_ip(interfaces) == (None, None)
