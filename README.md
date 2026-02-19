# Delinea Secret Server — AWX/AAP Credential Plugin

<!-- Badges -->
[![CI](https://github.com/acedya/tss-credential-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/acedya/tss-credential-plugin/actions/workflows/ci.yml)
[![Release](https://github.com/acedya/tss-credential-plugin/actions/workflows/release.yml/badge.svg)](https://github.com/acedya/tss-credential-plugin/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/awx-delinea-secret-server-credential-plugin)](https://pypi.org/project/awx-delinea-secret-server-credential-plugin/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/awx-delinea-secret-server-credential-plugin)](https://pypi.org/project/awx-delinea-secret-server-credential-plugin/)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](tests/)
[![License](https://img.shields.io/pypi/l/awx-delinea-secret-server-credential-plugin)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

> Custom AWX/AAP managed credential plugin for **Delinea (Thycotic) Secret Server**.
> Authenticates via OAuth2 at job launch, retrieves a short-lived token, and injects it into the runtime — the **raw password is never exposed** to the running job.

---

## Architecture

```
┌──────────────────────┐
│   AAP / AWX          │
│                      │
│  ┌────────────────┐  │       POST /oauth2/token
│  │ Credential     │──│──────────────────────────────┐
│  │ Plugin         │  │                              │
│  │ (Python)       │◄─│──────────────────────────────┤
│  └───────┬────────┘  │      { "access_token": ... } │
│          │           │                              │
│          ▼           │                    ┌─────────┴──────────┐
│  ┌────────────────┐  │                    │ Delinea Secret     │
│  │ Injector       │  │                    │ Server             │
│  │ (env + extras) │  │                    │ (OAuth2 endpoint)  │
│  └───────┬────────┘  │                    └────────────────────┘
│          │           │
│          ▼           │
│  ┌────────────────┐  │
│  │ Ansible Job    │  │
│  │ (playbook)     │  │
│  │                │  │
│  │ TSS_TOKEN ✔    │  │
│  │ PASSWORD  ✘    │  │
│  └────────────────┘  │
└──────────────────────┘
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Development](#development)
- [Plugin Details](#plugin-details)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Release Process](#release-process)
- [Deployment to AAP/AWX](#deployment-to-aapawx)
- [Usage in Playbooks](#usage-in-playbooks)
- [Repository Hardening](#repository-hardening)
- [Contributing](#contributing)

---

## Quick Start

### Install

```bash
pip install awx-delinea-secret-server-credential-plugin
```

Then on every AWX/AAP node:

```bash
awx-manage setup_managed_credential_types
```

### Do I need the `credential_type/` YAML files?

**No.** This package uses the AWX managed credential plugin pattern:
- It exposes a `CredentialPlugin` object through Python entry points
- Input schema is defined in Python (`inputs`)
- AWX discovers it via `awx-manage setup_managed_credential_types`

The `credential_type/` YAML files are kept as reference only.

---

## Development

### Prerequisites

- Python 3.8+
- GNU Make
- Git

### Setup

```bash
git clone https://github.com/acedya/tss-credential-plugin.git
cd tss-credential-plugin
make install-dev      # creates .venv, installs package + dev deps
```

### Makefile Reference

The Makefile is the **single source of truth** — CI workflows call `make` targets, so local and CI behavior stay perfectly aligned.

| Target | Description |
|--------|-------------|
| `make help` | Show all available targets |
| `make install-dev` | Install package with dev dependencies in `.venv` |
| `make format` | Auto-format code (black + isort) |
| `make lint` | CI-equivalent lint checks (black, isort, flake8, mypy) |
| `make test` | Run unit tests |
| `make test-ci` | CI-equivalent tests with coverage XML |
| `make build` | Build source + wheel distributions |
| `make release-check` | Build + twine check |
| `make ci` | Full CI-equivalent run: lint + test-ci + build |
| `make release-tag TAG=v0.2.1 [PUSH=1]` | Safe validated release tag creation |
| `make clean` | Remove caches, bytecode, build artifacts |

### Project Structure

```
.
├── credential_plugins/
│   ├── __init__.py
│   └── delinea_secret_server.py       # Main plugin module
├── tests/
│   ├── __init__.py
│   └── test_delinea_credential_plugin.py
├── credential_type/                   # Reference YAML (not used at runtime)
├── examples/
│   └── example_playbook.yaml
├── scripts/
│   └── release.sh                     # Safe tag helper
├── .github/workflows/
│   ├── ci.yml                         # Test / lint / build
│   └── release.yml                    # TestPyPI / PyPI / GitHub Release
├── pyproject.toml                     # Package metadata + tool config
├── Makefile                           # Single source of truth for CI
├── CHANGELOG.md                       # Release notes
└── README.md
```

---

## Plugin Details

### Credential Input Fields

| Field | Type | Required | Secret | Description |
|-------|------|----------|--------|-------------|
| `server_url` | string | Yes | No | Base URL (e.g. `https://myserver/SecretServer`) |
| `username` | string | Yes | No | Application user name |
| `password` | string | Yes | Yes | Password (encrypted at rest by AAP) |
| `domain` | string | No | No | Application user domain |

### Injector Output

The plugin injects **only** the OAuth2 token and server URL — never the raw password.

| Type | Variable | Value |
|------|----------|-------|
| Environment | `TSS_SERVER_URL` | Secret Server URL |
| Environment | `TSS_TOKEN` | OAuth2 access token |
| Extra var | `tss_server_url` | Secret Server URL |
| Extra var | `tss_token` | OAuth2 access token |

### Implementation

- **`_get_access_token(server_url, username, password, domain, verify_ssl)`**
  POSTs to `{server_url}/oauth2/token` with `grant_type=password`. Returns the `access_token` string. Raises `requests.HTTPError` on failure, `KeyError` if token missing.

- **`backend(credential_params)`**
  AWX entry point called at job launch. Calls `_get_access_token()`, returns `{"tss_token": ..., "tss_server_url": ...}`.

### OAuth2 Token Flow

```http
POST {server_url}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username={username}&password={password}&domain={domain}
```

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1200
}
```

---

## Testing

### Run Tests

```bash
make ci               # full CI parity: lint + test + build
make test             # unit tests only
make test-ci          # tests with coverage XML
make test-verbose     # verbose output
make lint             # lint checks only
```

### Test Matrix

| Test | Description |
|------|-------------|
| `test_get_access_token_success` | Token returned on successful OAuth2 call |
| `test_get_access_token_without_domain` | Domain is optional, absent from request |
| `test_get_access_token_http_error` | `HTTPError` raised on non-2xx |
| `test_get_access_token_missing_key` | `KeyError` raised when `access_token` missing |
| `test_backend_returns_token_and_url` | `backend()` returns expected dict |
| `test_backend_password_not_in_output` | Raw password never in plugin output |

### Dependencies

`pytest`, `pytest-cov`, `responses` (HTTP mocking), `black`, `isort`, `flake8`, `mypy` — all installed via `make install-dev`.

---

## CI/CD Pipeline

### Design Principles

- **Makefile = source of truth**: workflows call `make` targets, never duplicate shell commands
- **Local reproducibility**: `make ci` ≡ `ci.yml`, `make release-check` ≡ `release.yml` build step
- **OIDC Trusted Publishing**: no API token secrets stored in GitHub

### Workflows

| Workflow | Trigger | Jobs |
|----------|---------|------|
| `ci.yml` | Push to `main`, pull requests | Test (matrix: 3.10, 3.11), Lint, Build |
| `release.yml` | Tag `v*.*.*`, manual dispatch | PyPI + GitHub Release (tags), TestPyPI (manual) |

### Trusted Publishing Setup

This repository uses **PyPI OIDC Trusted Publishing** — no API token secrets required.

Create two trusted publisher configurations on [pypi.org](https://pypi.org) and [test.pypi.org](https://test.pypi.org):

| Setting | Value |
|---------|-------|
| Owner | Your GitHub org/user |
| Repository | `tss-credential-plugin` |
| Workflow | `release.yml` |
| Environment | `pypi` (production) / `testpypi` (staging) |

**Publish triggers:**
- **PyPI + GitHub Release**: strict `vX.Y.Z` tags, only if the tagged commit is on `main`
- **TestPyPI**: manual workflow dispatch (for pre-release validation)

Release notes are populated from `CHANGELOG.md`.

### Local Publish Fallback

Token-based publishing is available for emergencies:

```bash
make publish-testpypi-token TEST_PYPI_API_TOKEN=pypi-...
make publish-pypi-token PYPI_API_TOKEN=pypi-...
```

---

## Release Process

### Branching Model — [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)

This project follows **GitHub Flow**, the simplest branching model:

1. **`main`** is always deployable
2. **Create a branch** from `main` with a descriptive name (e.g. `add-ssl-toggle`, `fix-token-parsing`)
3. **Commit** your changes and push early for visibility
4. **Open a pull request** to start discussion and trigger CI
5. **Review & approve** — CI must pass, at least one approval required
6. **Merge to `main`** — branch is deleted after merge
7. **Tag & release** when ready: `make release-tag TAG=vX.Y.Z PUSH=1`

### Creating a Release

```bash
# 1. Update CHANGELOG.md with the new version notes
# 2. Create and validate the tag
make release-tag TAG=v0.2.1

# 3. Push when ready (triggers PyPI publish + GitHub Release)
make release-tag TAG=v0.2.1 PUSH=1
```

### Safety Checks (`scripts/release.sh`)

The release helper enforces:
- Strict `vX.Y.Z` semver format
- Must be on `main` branch
- Clean git working tree
- Tag must not exist locally or on `origin`
- `make ci` must pass before tag creation

Server-side guard: `release.yml` verifies the tagged commit is an ancestor of `origin/main`.

---

## Deployment to AAP/AWX

1. **Install the plugin** on AWX/AAP nodes (or build a custom Execution Environment)
   ```bash
   pip install awx-delinea-secret-server-credential-plugin
   ```

2. **Register credential types**
   ```bash
   awx-manage setup_managed_credential_types
   ```

3. **Create a Credential** using the *Delinea Secret Server* type — fill in `server_url`, `username`, `password`, and optionally `domain`

4. **Attach to a Job Template** — the token is injected at launch time as env vars and extra vars

---

## Usage in Playbooks

### Via extra vars (recommended)

```yaml
- name: Retrieve a secret from Delinea Secret Server
  ansible.builtin.debug:
    msg: >-
      {{ lookup('delinea.ss.tss', 42,
                server_url=tss_server_url,
                token=tss_token) }}
```

### Via environment variables

```yaml
- name: Use environment variables
  ansible.builtin.debug:
    msg: >-
      Server: {{ lookup('env', 'TSS_SERVER_URL') }}
      Token:  {{ lookup('env', 'TSS_TOKEN') }}
```

---

## Repository Hardening

Apply these in GitHub UI: **Settings → Rules → Rulesets**.

### Branch Protection

**`main`:**
- Require pull request with at least 1 approval
- Dismiss stale approvals on new commits
- Require status checks: CI jobs from `ci.yml`
- Require conversation resolution
- Block force pushes and branch deletion

### Tag Protection

**`v*.*.*` tags:**
- Restrict creation/update/deletion to maintainers only
- Works with local guard (`scripts/release.sh`) and workflow guard (`release.yml`)

### Environment Protection

| Environment | Configuration |
|-------------|---------------|
| `pypi` | Required reviewers (recommended), limit to protected branches/tags |
| `testpypi` | Optional reviewers for staging control |

---

## Contributing

### Workflow

1. Create a branch from `main` with a descriptive name
2. Make changes, run `make format` before committing
3. Push and open a pull request — CI runs automatically
4. Get review, iterate, then merge to `main`

### Roadmap

- [ ] Client credentials grant (SDK-based auth)
- [ ] Configurable `verify_ssl` toggle in credential input
- [ ] Token caching for rapid successive lookups
- [ ] Custom Execution Environment image with plugin pre-installed
- [ ] Integration tests against a real Secret Server instance

---

## License

[Apache-2.0](LICENSE)
