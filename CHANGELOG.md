# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
