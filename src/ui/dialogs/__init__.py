"""Top-level QDialog subclasses, one per file.

Re-exported here so callers can write:

    from src.ui.dialogs import AddAccountDialog, SettingsDialog, ...

without caring which file each one lives in.
"""

from .account_manager import AccountManagerDialog
from .add_account import AddAccountDialog
from .firewall_rule import FirewallRuleDialog
from .settings import SettingsDialog
from .ssh_key import SSHKeyDialog

__all__ = [
    "AccountManagerDialog",
    "AddAccountDialog",
    "FirewallRuleDialog",
    "SSHKeyDialog",
    "SettingsDialog",
]
