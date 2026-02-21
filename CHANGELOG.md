# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [0.2.3] - 2026-02-21

### Fixed
- Use `authorizer.get_access_token()` instead of `authorizer.token` to match the `python-tss-sdk` API.
- Podman deployment commands: run as root (`-u 0`), `--force-reinstall`, register credential types on both containers, and restart after install.
- Restore lost execute bit on `scripts/release.sh`.

### Added
- `make test-integration` target for running integration tests against a live Secret Server (credentials loaded from `.env`).
- Self-signed certificate documentation (`REQUESTS_CA_BUNDLE`) in README.
- `.env.example` exception in `.gitignore`.

### Changed
- Exclude integration tests from unit test / CI targets (`--ignore=test_integration.py`).
- Normalize line endings to LF across all files.
- Trim completed items from README roadmap.

## [0.2.2] - 2026-02-20

### Fixed
- Release script now auto-syncs `pyproject.toml` version from the tag before building.
- Use `patch.object()` in tests to fix Python 3.10 mock name-shadowing issue.
- License badge uses static shield (no PyPI dependency).

## [0.2.0] - 2026-02-19

### Added
- Managed AWX credential plugin packaging with `awx.credential_plugins` entry point.
- Python project metadata and build configuration via `pyproject.toml`.
- GitHub Actions CI workflow for test, lint, build, TestPyPI publish, PyPI publish, and release.
- Makefile targets for local virtual environment, dev install, tests, and package build.

### Changed
- Migrated from manual credential-type YAML artifacts to managed plugin pattern.
- Refactored credential plugin input labels and module exports for cleaner AWX integration.
- Switched publishing to GitHub OIDC Trusted Publishing (no API token secrets required).

### Removed
- Legacy GitLab CI pipeline configuration.
- Redundant `credential_type` YAML files from active plugin flow.
