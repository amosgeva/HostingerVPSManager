# Contributing to Hostinger VPS Manager

Thanks for considering a contribution! This is a public GPLv3 desktop app and we
want to keep it healthy and welcoming.

## Quick start

```bash
# 1. Fork on GitHub, then clone your fork
git clone https://github.com/<your-user>/HostingerVPSManager.git
cd HostingerVPSManager

# 2. Create a virtual environment (Python 3.10+)
python -m venv .venv
# Windows:    .venv\Scripts\activate
# Linux/Mac:  source .venv/bin/activate

# 3. Install in editable mode with dev tools
pip install -e ".[dev]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Run the app
python run.py
```

## Branch model

- `main` is always shippable.
- Feature work happens on `feature/<short-name>` branches.
- Bug fixes happen on `fix/<short-name>` branches.
- Open one PR per logical change. Small, focused PRs review faster.

## Commit messages

Follow the conventional-commits prefix the project already uses
(`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `ci:`):

```
feat: add backup management tab
fix: avoid double-restart when API returns 502
docs: clarify Linux keyring backend setup
```

The body should explain *why* the change is needed; the diff already shows what.

## Code style

- We use [`ruff`](https://docs.astral.sh/ruff/) for linting and formatting; the
  config lives in `pyproject.toml`.
- We use [`pylint`](https://pylint.readthedocs.io/) with a strict allowlist
  (`.codacy/tools-configs/pylint.rc`). New rules need a justification in the PR.
- We use [`bandit`](https://bandit.readthedocs.io/) for security linting.
- All checks run in `pre-commit` and in CI; please run them locally before
  pushing:

```bash
pre-commit run --all-files
pylint src/
bandit -r src/
```

## Tests

We don't have a test suite yet (it lands in v1.3 — see the project plan).
When you add new logic, prefer placing it in pure-Python modules under
`src/app/`, `src/core/` (Phase 3 layout) so it can eventually be tested
without spinning up Qt.

Once `pytest` lands:

```bash
pytest
```

## Reporting bugs

Open an issue and include:

- OS + Python version
- App version (shown in the title bar)
- Reproduction steps
- The relevant log lines (the app logs to stderr)
- Whether the failure is reproducible or transient

Please **never** paste an API token into an issue. If you suspect a token has
been exposed, rotate it immediately in the
[Hostinger Dashboard](https://hpanel.hostinger.com/).

## Pull request checklist

Before opening a PR:

- [ ] `pre-commit run --all-files` passes
- [ ] `pylint src/` passes
- [ ] App still launches and your change works manually
- [ ] CHANGELOG.md updated under the `## [Unreleased]` section
- [ ] PR description explains the *why* and links any related issue

We'll review as soon as we can. Smaller PRs land faster.

## Security

If you find a security issue, **do not** open a public GitHub issue. Email
`amos@geva.solutions` with details. We aim to respond within 72 hours.

## License

By contributing, you agree that your contribution is licensed under
[GPLv3](LICENSE).
