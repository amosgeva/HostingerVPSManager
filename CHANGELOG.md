# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
