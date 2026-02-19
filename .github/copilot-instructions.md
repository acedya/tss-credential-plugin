# Copilot Repository Instructions

## Project Overview

This is an **AWX/AAP managed credential plugin** for Delinea (Thycotic) Secret Server, packaged as a Python pip-installable library. It authenticates via OAuth2 at Ansible job launch time and injects a short-lived access token — never the raw password.

- **Package name**: `awx-delinea-secret-server-credential-plugin`
- **Entry point**: `awx.credential_plugins` → `credential_plugins:delinea_secret_server`
- **Python**: 3.8+ (tested on 3.10, 3.11)
- **Build system**: setuptools via `pyproject.toml`

## Architecture

The plugin is a single Python module (`credential_plugins/delinea_secret_server.py`) that:
1. Receives credential fields from AWX (server_url, username, password, domain)
2. POSTs to `{server_url}/oauth2/token` to get an OAuth2 access token
3. Returns `tss_token` and `tss_server_url` which AWX injects as env vars and extra vars
4. The raw password is **never** returned or injected

Key objects:
- `INPUTS` dict: defines the AWX credential input form schema
- `INJECTORS` dict: defines what gets injected into the job runtime
- `CredentialPlugin` namedtuple: the entry point AWX discovers
- `_get_access_token()`: internal function handling the OAuth2 POST
- `backend()`: entry point called by AWX at job launch

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
- HTTP mocking: `responses` library (never make real HTTP calls in tests)
- Test file: `tests/test_delinea_credential_plugin.py`
- Coverage target: 97%+
- All tests must pass: `make test-ci`
- Security invariant: **raw password must never appear in plugin output** — always write a test for this

When writing new tests:
- Mock all HTTP calls with `@responses.activate`
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
- `credential_type/` — YAML reference files (not used at runtime)
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

- This plugin runs inside AWX/AAP Python environments — keep dependencies minimal (`requests` only)
- Do not add heavy frameworks or unnecessary dependencies
- The `CredentialPlugin` namedtuple interface is defined by AWX — do not change its structure
- `inputs` and `injectors` dict shapes are AWX API contracts
- Maintain backward compatibility with Python 3.8
