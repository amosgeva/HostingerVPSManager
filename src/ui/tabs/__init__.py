"""Tab widgets — one per feature.

Each tab is a passive `QWidget`: it connects to its controller's
`pyqtSignal`s in `__init__` and renders the corresponding state. User
actions are routed back to the controller via its public methods. The
tab does not own any business state.
"""

from .firewall_tab import FirewallTab

__all__ = ["FirewallTab"]
