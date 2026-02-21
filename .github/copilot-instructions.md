# Copilot Repository Instructions

## Project Overview

This is an **AWX/AAP external credential plugin** for Delinea (Thycotic) Secret Server, packaged as a Python pip-installable library. It authenticates via OAuth2 at Ansible job launch time and returns a short-lived access token through AWX credential linking — never the raw password.

- **Package name**: `awx-delinea-secret-server-credential-plugin`
- **Entry point**: `awx.credential_plugins` → `credential_plugins:delinea_secret_server`
- **Python**: 3.8+ (tested on 3.10, 3.11)
- **Build system**: setuptools via `pyproject.toml`

## Architecture

The plugin is a single Python module (`credential_plugins/delinea_secret_server.py`) that:
1. Receives credential fields + metadata from AWX as **kwargs (base_url, username, password, domain, identifier)
2. Uses the Delinea Python SDK (`python-tss-sdk`) to authenticate via OAuth2
3. Returns a **single string** based on the `identifier` metadata dropdown (`token` or `base_url`)
4. The raw password is **never** returned

This plugin is an **external credential source** — it does NOT include injectors. To inject values into jobs, users create a separate target credential type with injectors and link its fields to this plugin.

Key objects:
- `INPUTS` dict: defines the AWX credential input form schema (`fields` for auth, `metadata` for per-link dropdown)
- `CredentialPlugin` namedtuple: the entry point AWX discovers — exactly 3 fields: `name`, `inputs`, `backend`
- `_get_authorizer()`: creates a `PasswordGrantAuthorizer` or `DomainPasswordGrantAuthorizer` from the SDK
- `backend(**kwargs)`: entry point called by AWX at job launch, returns a single string value

## Code Style & Conventions

- **Formatter**: `black` with `line-length = 100`
- **Import sorter**: `isort` with `profile = "black"`, `line_length = 100`
- **Linter**: `flake8` with `max-line-length = 100`
- **Type checker**: `mypy` with `ignore_missing_imports = true`
- Always run `make format` before committing
- Use type annotations on all new function signatures
- Prefer `Optional[str]` over `str | None` (Python 3.8 compat)
- Use `Dict`, `Any`, `Optional` from `typing` module (not built-in generics)

## Testing

- Framework: `pytest` with `pytest-cov`
- SDK mocking: `unittest.mock` (never make real HTTP calls in tests)
- Test file: `tests/test_delinea_credential_plugin.py`
- Coverage target: 97%+
- All tests must pass: `make test-ci`
- Security invariant: **raw password must never appear in plugin output** — always write a test for this

When writing new tests:
- Mock SDK classes with `unittest.mock.patch`
- Test both success and error paths
- Verify that sensitive data (passwords) is never leaked in return values
- Use descriptive test names: `test_<function>_<scenario>`

## Build & CI

- **Makefile is the single source of truth** for all CI/build/release commands
- GitHub Actions workflows (`ci.yml`, `release.yml`) call `make` targets directly
- Local CI reproduction: `make ci` (lint + test-ci + build)
- Never duplicate shell commands between Makefile and workflow files
- Virtual environment path: `.venv` (do not use system Python)
- Dependencies are declared in `pyproject.toml` under `[project.optional-dependencies] dev`

## File Organization

- `credential_plugins/` — plugin source (keep flat, single module)
- `tests/` — unit tests
- `scripts/` — release automation helpers
- `examples/` — sample Ansible playbooks

## Branching Model

This project follows **GitHub Flow** (https://docs.github.com/en/get-started/using-github/github-flow):
- `main` is always deployable — all work branches from and merges back to `main`
- Create descriptive branch names (e.g. `add-ssl-toggle`, `fix-token-parsing`)
- Open pull requests for review — CI must pass before merge
- No `develop` or long-lived integration branches
- Releases are tagged from `main` only

## Release Process

- Versioning: strict semantic versioning (`vX.Y.Z` tags)
- Releases only from `main` branch
- Tag creation: `make release-tag TAG=vX.Y.Z [PUSH=1]`
- Publishing: OIDC Trusted Publishing via GitHub Actions (no API tokens)
- Always update `CHANGELOG.md` before tagging
- Always update `version` in `pyproject.toml` before tagging

## Important Constraints

- This plugin runs inside AWX/AAP Python environments — keep dependencies minimal (`python-tss-sdk` only)
- Do not add heavy frameworks or unnecessary dependencies
- The `CredentialPlugin` namedtuple interface is defined by AWX — do not change its structure
- `inputs` dict shape is an AWX API contract
- Maintain backward compatibility with Python 3.8
