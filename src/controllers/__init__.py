"""ViewModels for the MVVM-lite-via-Qt-signals architecture.

Each controller owns the state for one feature, exposes `pyqtSignal`s for
state changes, and **does not import `PyQt6.QtWidgets`** (only `QtCore`
for `QObject` + `pyqtSignal`). Views (`src/ui/tabs/...`) connect to the
signals and call the controller's public methods on user action.

Headless-testable via `pytest-qt`'s `qtbot.waitSignal` and a
`MagicMock(spec=HostingerAPIClient)` — see
`tests/unit/controllers/`.
"""

from .firewall_controller import FirewallController

__all__ = ["FirewallController"]
