# Delinea Secret Server — AWX/AAP Credential Plugin

<!-- Badges -->
[![CI](https://github.com/acedya/tss-credential-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/acedya/tss-credential-plugin/actions/workflows/ci.yml)
[![Release](https://github.com/acedya/tss-credential-plugin/actions/workflows/release.yml/badge.svg)](https://github.com/acedya/tss-credential-plugin/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/awx-delinea-secret-server-credential-plugin)](https://pypi.org/project/awx-delinea-secret-server-credential-plugin/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/awx-delinea-secret-server-credential-plugin)](https://pypi.org/project/awx-delinea-secret-server-credential-plugin/)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](tests/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

> Custom AWX/AAP credential plugin for **Delinea (Thycotic) Secret Server**.
> Uses the official **Delinea Python SDK** (`python-tss-sdk`) to authenticate via OAuth2 at job launch, retrieves a short-lived access token, and provides it through AWX credential linking — the **raw password is never exposed** to the running job.

---

## Architecture

```
┌───────────────────────────────┐
│   AAP / AWX                   │
│                               │
│  ┌─────────────────────────┐  │    python-tss-sdk (OAuth2)
│  │ Delinea SS Credential   │──│──────────────────────────────┐
│  │ (External – Plugin)     │  │                              │
│  │  base_url, user, pass   │◄─│──────────────────────────────┤
│  └────────────┬────────────┘  │      { "access_token": ... } │
│               │ credential    │                              │
│               │ linking       │                    ┌─────────┴──────────┐
│               ▼               │                    │ Delinea Secret     │
│  ┌─────────────────────────┐  │                    │ Server             │
│  │ Target Credential       │  │                    │ (OAuth2 endpoint)  │
│  │ (fields linked via      │  │                    └────────────────────┘
│  │  identifier dropdown)   │  │
│  └────────────┬────────────┘  │
│               │ injected by   │
│               │ target type   │
│               ▼               │
│  ┌─────────────────────────┐  │
│  │ Ansible Job (playbook)  │  │
│  │                         │  │
│  │  TSS_TOKEN  ✔           │  │
│  │  PASSWORD   ✘           │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
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
- [Credential Linking](#credential-linking)
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

### Do I need a separate credential type in AWX?

**Yes — for injection.** This plugin is an *external credential source* (it resolves values). To inject those values into your Ansible jobs as environment variables or extra vars, you need a **target credential type** with injectors. See [Credential Linking](#credential-linking) for the recommended setup.

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
├── examples/
│   └── example_playbook.yaml
├── scripts/
│   └── release.sh                     # Safe tag helper
├── .github/workflows/
│   ├── ci.yml                         # Test / lint / build
│   └── release.yml                    # PyPI publish / GitHub Release
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
| `base_url` | string | Yes | No | Base URL (e.g. `https://myserver/SecretServer`) |
| `username` | string | Yes | No | Application user name |
| `password` | string | Yes | Yes | Password (encrypted at rest by AAP) |
| `domain` | string | No | No | Application user domain |

### Injector Output

This plugin is an **external credential source** — it does _not_ define its own injectors.
AWX calls `backend(**kwargs)` and uses the returned value to populate a linked credential field.

The `identifier` metadata dropdown selects what the plugin returns:

| Identifier | Returns |
|------------|--------|
| `token` (default) | OAuth2 access token |
| `base_url` | Secret Server base URL (pass-through) |

To inject values as environment variables or extra vars, create a **target credential type**
with those injectors, then link its fields to this plugin (see [Credential Linking](#credential-linking) below).

### Implementation

- **`_get_authorizer(base_url, username, password, domain)`**
  Creates a `PasswordGrantAuthorizer` or `DomainPasswordGrantAuthorizer` from `python-tss-sdk`.
  The SDK handles the OAuth2 `password` grant internally.

- **`backend(**kwargs)`**
  AWX entry point called at job launch. Receives all `fields` and `metadata` as keyword arguments.
  Returns a **single string** based on the `identifier` metadata dropdown value (`token` or `base_url`).

### Self-Signed Certificates

When using a self-signed certificate for SSL, the `REQUESTS_CA_BUNDLE` environment variable should be set to the path of the certificate (in `.pem` format). This will negate the need to ignore SSL certificate verification, which makes your application vulnerable.

```bash
export REQUESTS_CA_BUNDLE=/path/to/your/ca-bundle.pem
```

Please reference the [requests documentation](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification) for further details on the `REQUESTS_CA_BUNDLE` environment variable, should you require it.

> **Note:** On RHEL / CentOS systems the system CA bundle is typically located at `/etc/pki/tls/cert.pem`.

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
| `test_get_authorizer_without_domain` | Uses `PasswordGrantAuthorizer` when domain absent |
| `test_get_authorizer_with_domain` | Uses `DomainPasswordGrantAuthorizer` when domain set |
| `test_backend_returns_token` | Returns token when identifier is `token` |
| `test_backend_defaults_to_token` | Defaults to `token` when identifier omitted |
| `test_backend_token_with_domain` | Uses domain authorizer and returns token |
| `test_backend_returns_base_url` | Returns base URL when identifier is `base_url` |
| `test_backend_raises_on_unknown_identifier` | `ValueError` raised for unknown identifier |
| `test_backend_password_not_in_output` | Raw password never in plugin output |
| `test_backend_sdk_error_propagates` | SDK authentication errors propagate to AWX |
| `test_inputs_has_required_fields` | INPUTS declares expected authentication fields |
| `test_inputs_password_is_secret` | Password field is marked as secret |
| `test_inputs_metadata_has_identifier` | Metadata includes `identifier` dropdown |
| `test_inputs_identifier_has_choices` | Identifier has `token` / `base_url` choices |
| `test_inputs_identifier_has_default` | Identifier defaults to `token` |
| `test_inputs_required_includes_identifier` | `identifier` is listed as required |
| `test_credential_plugin_structure` | CredentialPlugin has exactly 3 fields |
| `test_credential_plugin_no_injectors` | Plugin does not include injectors |
| `test_credential_plugin_name` | Plugin name matches AWX UI display |
| `test_credential_plugin_inputs_is_inputs` | Plugin references module-level INPUTS |
| `test_credential_plugin_backend_is_callable` | Plugin backend is callable |

### Dependencies

`pytest`, `pytest-cov`, `black`, `isort`, `flake8`, `mypy` — all installed via `make install-dev`. Tests mock the SDK with `unittest.mock`.

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
| `release.yml` | Tag `v*.*.*` | PyPI publish + GitHub Release |

### Trusted Publishing Setup

This repository uses **PyPI OIDC Trusted Publishing** — no API token secrets required.

Create a trusted publisher configuration on [pypi.org](https://pypi.org):

| Setting | Value |
|---------|-------|
| Owner | Your GitHub org/user |
| Repository | `tss-credential-plugin` |
| Workflow | `release.yml` |
| Environment | `pypi` |

**Publish trigger:** strict `vX.Y.Z` tags, only if the tagged commit is on `main`.

Release notes are populated from `CHANGELOG.md`.

### Local Publish Fallback

Token-based publishing is available for emergencies:

```bash
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

### Containerised AAP (single-node / podman)

The plugin must be installed inside **both** controller containers (`automation-controller-web` and `automation-controller-task`).

**Install from GitHub (quickest):**

```bash
podman exec -it -u 0 automation-controller-web awx-python -m pip install git+https://github.com/acedya/tss-credential-plugin.git --force-reinstall
podman exec -it -u 0 automation-controller-task awx-python -m pip install git+https://github.com/acedya/tss-credential-plugin.git --force-reinstall
podman exec -it -u 0 automation-controller-web awx-manage setup_managed_credential_types
podman exec -it -u 0 automation-controller-task awx-manage setup_managed_credential_types
podman restart automation-controller-web
podman restart automation-controller-task
```

**Install from a local wheel:**

```bash
# Build on your dev machine
make build

# Copy the wheel to the AAP host
scp dist/awx_delinea_secret_server_credential_plugin-*.whl admin@<aap-host>:/tmp/

# Copy into the containers
podman cp /tmp/awx_delinea_secret_server_credential_plugin-*.whl automation-controller-web:/tmp/
podman cp /tmp/awx_delinea_secret_server_credential_plugin-*.whl automation-controller-task:/tmp/

# Install
podman exec -it -u 0 automation-controller-web awx-python -m pip install /tmp/awx_delinea_secret_server_credential_plugin-*.whl
podman exec -it -u 0 automation-controller-task awx-python -m pip install /tmp/awx_delinea_secret_server_credential_plugin-*.whl

# Register
podman exec -it -u 0 automation-controller-web awx-manage setup_managed_credential_types
podman exec -it -u 0 automation-controller-task awx-manage setup_managed_credential_types
podman restart automation-controller-web
podman restart automation-controller-task
```

> **Note:** `pip install` inside containers is ephemeral — reinstall after container restarts, or build a custom controller image for persistence.

### Standard (non-containerised) install

1. **Install the plugin**
   ```bash
   awx-python -m pip install awx-delinea-secret-server-credential-plugin
   ```

2. **Register credential types**
   ```bash
   awx-manage setup_managed_credential_types
   ```

### After installation

1. **Create a "Delinea Secret Server" credential** — fill in `base_url`, `username`, `password`, and optionally `domain`

2. **Link to a target credential** — see [Credential Linking](#credential-linking) below

---

## Credential Linking

This plugin is an **external credential source**. It authenticates to Secret Server and returns a value (token or base URL) that AWX injects into a linked credential field.

To use the plugin you need **two things** in AWX:
1. A **custom credential type** (defines the fields + injectors for your jobs)
2. A **Delinea Secret Server credential** (the source — authenticates to Secret Server)

Then you create a credential of your custom type and **link** its fields to the Delinea credential.

### Step 1 — Create the Target Credential Type

Go to **Administration → Credential Types → Add**.

| Setting | Value |
|---------|-------|
| **Name** | `Delinea Secret Server Token` (or any name you prefer) |
| **Description** | Injects a Delinea SS OAuth2 token and base URL |

**Input Configuration** (paste as YAML):

```yaml
fields:
  - id: tss_token
    label: TSS Token
    type: string
    secret: true
  - id: tss_base_url
    label: TSS Base URL
    type: string
required:
  - tss_token
  - tss_base_url
```

**Injector Configuration** (paste as YAML):

```yaml
env:
  TSS_TOKEN: '{{ tss_token }}'
  TSS_BASE_URL: '{{ tss_base_url }}'
extra_vars:
  tss_token: '{{ tss_token }}'
  tss_base_url: '{{ tss_base_url }}'
```

> **Tip:** Adjust the injectors to your needs — if you only need env vars, remove the `extra_vars` block (and vice versa).

Click **Save**.

### Step 2 — Create the Source Credential (Delinea Secret Server)

Go to **Resources → Credentials → Add**.

| Setting | Value |
|---------|-------|
| **Name** | `Delinea SS - Production` (or any name) |
| **Credential Type** | `Delinea Secret Server` (the plugin type — appears after installing the plugin and running `awx-manage setup_managed_credential_types`) |
| **Secret Server URL** | `https://myserver/SecretServer` or `https://mytenant.secretservercloud.com` |
| **Username** | Your application user username |
| **Password** | The corresponding password |
| **Domain** | *(optional)* Your AD domain if using domain auth |

Click **Save**.

### Step 3 — Create the Target Credential and Link Fields

Go to **Resources → Credentials → Add**.

| Setting | Value |
|---------|-------|
| **Name** | `Delinea SS Token - Production` (or any name) |
| **Credential Type** | `Delinea Secret Server Token` (the custom type from Step 1) |

Now link each field to the source credential:

1. **TSS Token** field — click the **key icon** (🔑) next to the field:
   - **Credential** → select `Delinea SS - Production`
   - **Output value** → select `token`
2. **TSS Base URL** field — click the **key icon** (🔑) next to the field:
   - **Credential** → select `Delinea SS - Production`
   - **Output value** → select `base_url`

Click **Save**.

### Step 4 — Attach to a Job Template

Go to **Resources → Templates** → edit your Job Template.

In the **Credentials** section, add the `Delinea SS Token - Production` credential (the target from Step 3).

At launch, AWX will:
1. Call the Delinea plugin to authenticate and get a fresh OAuth2 token
2. Inject `TSS_TOKEN` and `TSS_BASE_URL` as environment variables
3. Inject `tss_token` and `tss_base_url` as extra vars
4. Your playbook can use either method to access the values

---

## Usage in Playbooks

### Via extra vars (recommended)

```yaml
- name: Retrieve a secret from Delinea Secret Server
  ansible.builtin.debug:
    msg: >-
      {{ lookup('delinea.ss.tss', 42,
                base_url=tss_base_url,
                token=tss_token) }}
```

### Via environment variables

```yaml
- name: Use environment variables
  ansible.builtin.debug:
    msg: >-
      Server: {{ lookup('env', 'TSS_BASE_URL') }}
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

---

## Contributing

### Workflow

1. Create a branch from `main` with a descriptive name
2. Make changes, run `make format` before committing
3. Push and open a pull request — CI runs automatically
4. Get review, iterate, then merge to `main`

### Roadmap

- [ ] Custom Execution Environment image with plugin pre-installed

---

## License

[Apache-2.0](LICENSE)
