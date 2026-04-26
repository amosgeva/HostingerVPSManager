# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `src/workers/` — new package containing `APIWorker` (extracted from
  `main_window.py`) and a new `WorkerPool` lifetime manager. The pool
  retires workers automatically when `finished` / `error` fires
  (replacing the v1.1.0 stop-gap helpers) and provides cooperative
  shutdown: `requestInterruption()` first, `wait(timeout_ms)` for
  graceful exit, `terminate()` only as a last resort. `terminate()`
  used to be the default and skips `finally` blocks — a real
  reliability hazard.
- `tests/unit/workers/test_worker_pool.py` — 7 pytest-qt tests
  covering submit / retire-on-finish / retire-on-error / concurrent
  workers / shutdown drain / shutdown-no-op. Total suite now 58.
- `src/ui/dialogs/` — one file per `QDialog` subclass:
  `add_account.py`, `account_manager.py`, `firewall_rule.py`,
  `ssh_key.py`, `settings.py`, plus an `__init__.py` re-export.
- `src/app/resources.py` — small shared `get_resource_path` helper
  (was inlined on `MainWindow`; AccountManagerDialog needed it too).

### Changed

- `MainWindow.workers` (a list) and the v1.1.0 `_track_worker` /
  `_retire_worker` helpers are gone. Replaced by `self.worker_pool`
  (a `WorkerPool`). Every `self._track_worker(worker); worker.start()`
  pair (21 sites) collapses to `self.worker_pool.submit(worker)`.
  `perform_cleanup()` calls `self.worker_pool.shutdown()` instead of
  iterating `self.workers` and `terminate()`-ing.

- `MainWindow` no longer carries the five dialog classes (~490 lines
  deleted). It imports them from `src.ui.dialogs` instead. File now
  ≈ 2,000 lines, down from 2,502 at the start of the public-app
  upgrade effort.

- `src/core/network/ip_detect.py` — pure-function module containing the
  cross-platform LAN-IP detection that was inlined on `MainWindow`
  (`get_local_ip`, `find_best_ip`, `should_skip_interface`,
  `is_priority_interface`, `get_valid_ipv4`, plus the
  `PRIORITY_KEYWORDS` / `EXCLUDE_KEYWORDS` constants).
- `src/core/formatting/datacenter.py` — pure-function helpers for VM /
  data-center display strings (`get_os_name`,
  `format_datacenter_display`, `find_datacenter_by_id`,
  `format_datacenter_for_vm`).
- `tests/` — first pytest suite. **51 tests** across
  `test_ip_detect.py` and `test_datacenter_formatting.py`, all pure
  functions over plain dataclasses and `SimpleNamespace` fakes (no
  Qt, no real network, no mocks).
- `pytest` step in the CI lint matrix (Python 3.10–3.13).

### Changed

- `MainWindow` no longer carries IP-detection or datacenter/OS
  formatting methods (~135 lines deleted): `get_ethernet_ip`,
  `_get_ip_via_socket`, `_find_best_ip`,
  `_should_skip_interface`, `_is_priority_interface`,
  `_get_valid_ipv4`, `_get_os_name`, `_get_datacenter_text`,
  `_find_datacenter_by_id`, `_format_datacenter_display` are gone;
  call sites use the new free functions directly.

## [1.2.0] — Cross-platform

### Added

- macOS `.app` bundle output from `HostingerVPSManager.spec` (single
  unified spec; auto-detects platform).
- `.github/workflows/release.yml` — tag-driven release workflow that
  builds Windows / Linux / macOS artefacts on push of a `v*.*.*` tag and
  publishes them to a GitHub Release.
- Per-OS install instructions in `README.md`, including the Linux Qt
  system dependencies and the macOS Gatekeeper first-launch caveat.
- Keyring backend is now logged at startup (e.g. `Keyring backend:
  WinVaultKeyring`) so users can confirm which OS store is in use.

### Changed

- `_find_best_ip` now skips interfaces reporting down via
  `psutil.net_if_stats().isup`, and the exclude list covers macOS
  (`utun`, `awdl`, `gif`, `stf`, `bridge`) and Linux (`tun`, `tap`,
  `veth`, `br-`) virtual / VPN interfaces alongside the existing
  Windows ones.
- `quit_application` no longer assumes the tray icon exists.
- `start_minimized` is honoured only when a system tray is actually
  available; on tray-less systems the window is shown instead of
  hidden-with-no-recovery.
- `HostingerVPSManager.spec` only injects Windows-only hidden imports
  (`keyring.backends.Windows`, `win32timezone`) on Windows. Icon
  selection is OS-aware (`.ico` on Windows, `.png` everywhere else).
- `credentials.py` docstring no longer claims Windows-only support; it
  documents the per-OS keyring backend matrix.

## [1.1.0] — Foundations

### Added

- `pyproject.toml` (PEP 621) with runtime + dev dependency sets; install with
  `pip install -e ".[dev]"`.
- `src/app/constants.py` for centralised timing / URL / retry constants.
- HTTP retry with exponential backoff in `HostingerAPIClient` (`urllib3.Retry`),
  honouring `Retry-After` for 429 / 502 / 503 / 504 / 500 responses.
- Worker tracking helper (`MainWindow._track_worker`) that drops references to
  finished `APIWorker` threads so they no longer leak across the session.
- `CONTRIBUTING.md`, `CHANGELOG.md`, GitHub issue + PR templates.
- `.pre-commit-config.yaml` (ruff, bandit, basic hygiene hooks).
- `.github/workflows/ci.yml` running lint + build on Win/Linux/macOS.

### Changed

- `pywin32` is now a Windows-only dependency in `pyproject.toml` and
  `requirements.txt`, so `pip install` works on Linux and macOS.
- `get_data_center_by_id` and `get_subscription_by_id` use a lazy in-memory
  index, removing the N+1 round-trip on repeat lookups.
- App version is now sourced from `src/__init__.__version__` instead of
  hard-coded in `main.py`.

### Removed

- Legacy duplicate `hostinger_vps_manager.spec` (used the deprecated
  `block_cipher` syntax and was superseded by `HostingerVPSManager.spec`).
- Stale TypeScript/Node.js exclusions from `.codacy.yaml`.

## [1.0.0] — 2025

Initial public release of the Hostinger VPS Manager. Highlights:

- PyQt6 desktop UI for managing Hostinger VPS instances.
- Multi-account support with secure credential storage via OS keyring.
- VPS power controls, real-time CPU/RAM/disk metrics, uptime tracking.
- Firewall rule management, SSH key management, Monarx malware scanner status.
- Subscription + data-center information.
- System tray integration with status-change notifications.
- CSV export for action logs and metrics.
- Standalone Windows `.exe` build via PyInstaller.
