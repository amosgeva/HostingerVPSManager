"""Cross-platform "what is this machine's LAN IP?" detection.

Pure functions: no Qt imports, no `self`, no global state. Designed to
be unit-testable with synthetic `psutil.net_if_addrs()` /
`psutil.net_if_stats()` shapes — see tests/unit/core/test_ip_detect.py.

`psutil` is a soft dependency at this layer (the package as a whole
declares it as required, but importing this module on a system without
it falls back to a single-IP socket lookup instead of crashing).
"""

import socket
from collections.abc import Iterable
from typing import Any

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]


# Substring matches that suggest a physical NIC across the three OSes.
#   Linux:   eth*, enp*, eno*, ens*, wlan*, wlp*, wlo*
#   macOS:   en0 (Wi-Fi or first ethernet), en1, en2, ...
#   Windows: "Ethernet*", "Wi-Fi*", "Local Area Connection*"
PRIORITY_KEYWORDS: tuple[str, ...] = (
    "ethernet",
    "eth",
    "wi-fi",
    "wlan",
    "wl",
    "en",
)

# Substrings that mark a virtual / transient / VPN interface.
EXCLUDE_KEYWORDS: tuple[str, ...] = (
    # Cross-platform VPN / virtual
    "tailscale",
    "vpn",
    "virtual",
    "vmware",
    "vbox",
    "docker",
    "wsl",
    "loopback",
    # Windows Hyper-V / WSL
    "vethernet",
    # Linux VPN / virtual ethernet
    "tun",
    "tap",
    "veth",
    "br-",
    "bridge",
    # macOS
    "utun",
    "awdl",
    "gif",
    "stf",
    "anpi",
    "ap1",
    "llw",
    "ipsec",
)

UNAVAILABLE = "--"


def get_local_ip() -> str:
    """Best-effort detection of this machine's LAN IP. Returns "--" on failure."""
    if psutil is None:
        return _get_ip_via_socket()

    try:
        interfaces = psutil.net_if_addrs()
        try:
            stats = psutil.net_if_stats()
        except Exception:
            stats = None
        best_ip, fallback_ip = find_best_ip(interfaces, stats)
        return best_ip or fallback_ip or UNAVAILABLE
    except Exception:
        return UNAVAILABLE


def _get_ip_via_socket() -> str:
    """Fallback when psutil is unavailable."""
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return UNAVAILABLE


def find_best_ip(
    interfaces: dict[str, Any],
    stats: dict[str, Any] | None = None,
) -> tuple[str | None, str | None]:
    """Return (priority_ip, fallback_ip) from a `net_if_addrs()`-shaped dict.

    `priority_ip` is the IP of the first interface whose name matches
    one of `PRIORITY_KEYWORDS` and isn't in `EXCLUDE_KEYWORDS`. `fallback_ip`
    is the first non-excluded interface's IP encountered, used when no
    priority match is found.

    `stats` is an optional `net_if_stats()`-shaped dict; when provided,
    interfaces reporting `not stats[name].isup` are skipped.
    """
    fallback_ip = None

    for iface_name, addrs in interfaces.items():
        iface_lower = iface_name.lower()

        if stats is not None:
            iface_stats = stats.get(iface_name)
            if iface_stats is not None and not iface_stats.isup:
                continue

        if should_skip_interface(iface_lower):
            continue

        ip = get_valid_ipv4(addrs)
        if ip is None:
            continue

        if is_priority_interface(iface_lower):
            return (ip, fallback_ip)
        if fallback_ip is None:
            fallback_ip = ip

    return (None, fallback_ip)


def should_skip_interface(
    iface_lower: str,
    excludes: Iterable[str] = EXCLUDE_KEYWORDS,
) -> bool:
    """True if any of `excludes` is a substring of `iface_lower`."""
    return any(excl in iface_lower for excl in excludes)


def is_priority_interface(
    iface_lower: str,
    priorities: Iterable[str] = PRIORITY_KEYWORDS,
) -> bool:
    """True if any of `priorities` is a substring of `iface_lower`."""
    return any(prio in iface_lower for prio in priorities)


def get_valid_ipv4(addrs: Iterable[Any]) -> str | None:
    """Return the first non-loopback, non-link-local IPv4 address from `addrs`.

    Each entry in `addrs` is duck-typed: anything with `.family` and
    `.address` attributes (e.g. `psutil._common.snicaddr` or a test
    fake) works.
    """
    for addr in addrs:
        if addr.family == socket.AF_INET:
            ip = addr.address
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
    return None
