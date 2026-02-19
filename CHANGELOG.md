# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

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
