"""Shared pytest fixtures.

Right now this is mostly empty — the first batch of tests are pure
functions over plain dataclasses and `types.SimpleNamespace` fakes,
so they need no fixtures. As the controller / pytest-qt tests land
in subsequent Phase 3 PRs, fixtures (`fake_api_client`, `qtbot`
helpers, `worker_pool`) will move here.
"""
