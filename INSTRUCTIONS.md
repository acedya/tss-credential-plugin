# Delinea Secret Server — AAP/AWX Credential Plugin

## Project Overview

This project implements a **custom credential type and credential plugin** for Ansible Automation Platform (AAP) / AWX that integrates with **Delinea (Thycotic) Secret Server**.

The plugin authenticates against Secret Server's OAuth2 endpoint at job launch time, retrieves a short-lived access token, and injects it into the job runtime. The **raw password is never exposed** to the running job — only the token.

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

## Directory Structure

```
.
├── INSTRUCTIONS.md                              # This file
├── Makefile                                     # Test runner & utilities
├── credential_plugins/
│   ├── __init__.py
│   └── delinea_secret_server.py                 # Main plugin module
├── examples/
│   └── example_playbook.yaml                    # Sample playbook using the lookup
├── tests/
│   ├── __init__.py
│   └── test_delinea_credential_plugin.py        # Unit tests
├── requirements.txt                             # Python runtime dependencies
├── pyproject.toml                               # Package metadata + AWX entry point
├── .github/workflows/ci.yml                     # Test/lint/build checks
└── .github/workflows/release.yml                # TestPyPI/PyPI publish + GitHub Release
```

---

## Managed Credential Type Input Configuration

The managed credential type is defined directly in the Python plugin (`inputs`) and defines four fields. Three are required:

| Field        | Type   | Required | Secret | Description                                           |
|-------------|--------|----------|--------|-------------------------------------------------------|
| `server_url` | string | ✅       | No     | Base URL (e.g. `https://myserver/SecretServer`)       |
| `username`   | string | ✅       | No     | The (Application) user username                       |
| `password`   | string | ✅       | ✅     | The corresponding password (encrypted at rest by AAP) |
| `domain`     | string | No       | No     | The (Application) user domain                         |

---

## Injector Behavior

The injector exposes **only** the OAuth2 token and server URL:

### Environment Variables

| Variable         | Value                  |
|-----------------|------------------------|
| `TSS_SERVER_URL` | The Secret Server URL  |
| `TSS_TOKEN`      | The OAuth2 access token |

### Extra Variables

| Variable         | Value                  |
|-----------------|------------------------|
| `tss_server_url` | The Secret Server URL  |
| `tss_token`      | The OAuth2 access token |

> **Security:** The `password` field is **never** injected into environment variables or extra vars. Only the short-lived token is exposed.

---

## Plugin Implementation Details

### File: `credential_plugins/delinea_secret_server.py`

- **`_get_access_token(server_url, username, password, domain=None, verify_ssl=True)`**
  - POSTs to `{server_url}/oauth2/token` with `grant_type=password`
  - Sends `username`, `password`, and optionally `domain` as form-urlencoded body
  - Returns the `access_token` string from the JSON response
  - Raises `requests.HTTPError` on non-2xx responses
  - Raises `KeyError` if `access_token` is missing from the response

- **`backend(credential_params)`**
  - Entry point called by AWX/AAP at job launch time
  - Receives the saved credential fields as a dict
  - Calls `_get_access_token()` with the credential values
  - Returns a dict with keys `tss_token` and `tss_server_url`
  - The raw password **must never** appear in the returned dict

### OAuth2 Token Request Format

```http
POST {server_url}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username={username}&password={password}&domain={domain}
```

### Expected Response

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1200
}
```

---

## Testing

### Dependencies

- `pytest` — test framework
- `responses` — mock HTTP requests in tests

### Running Tests

```bash
# Full local CI parity (lint + test with coverage + build)
make ci

# Run only CI-equivalent lint checks
make lint

# Run only CI-equivalent tests with coverage.xml
make test-ci

# Build distributions and validate metadata
make release-check

# Run tests with verbose output
make test-verbose

# Clean up
make clean
```

### CI/Release Design Concept

- The Makefile is the single source of truth for commands.
- GitHub workflows call `make` targets directly, instead of duplicating shell commands.
- This guarantees local reproducibility:
  - `ci.yml` behavior ⇔ `make ci`
  - `release.yml` build/check behavior ⇔ `make release-check`
- Publishing in GitHub Actions uses OIDC Trusted Publishing.
- Local token-based publish commands are provided as a fallback:
  - `make publish-testpypi-token TEST_PYPI_API_TOKEN=...`
  - `make publish-pypi-token PYPI_API_TOKEN=...`

### Safe Tag Creation for Releases

Use the helper script through Makefile:

```bash
# Create local validated tag
make release-tag TAG=v0.2.1

# Create and push validated tag
make release-tag TAG=v0.2.1 PUSH=1
```

The helper performs:
- strict `vX.Y.Z` semver validation
- clean working tree check
- duplicate tag checks (local + origin)
- `make ci` before tag creation

### Test Cases

The following test cases **must** pass:

| Test                                    | Description                                                    |
|----------------------------------------|----------------------------------------------------------------|
| `test_get_access_token_success`         | Token returned on successful OAuth2 call                       |
| `test_get_access_token_without_domain`  | Domain is optional; must not appear in request if absent       |
| `test_get_access_token_http_error`      | `HTTPError` raised on non-2xx responses                        |
| `test_get_access_token_missing_key`     | `KeyError` raised when `access_token` missing from response    |
| `test_backend_returns_token_and_url`    | `backend()` returns the expected dict for AWX injection        |
| `test_backend_password_not_in_output`   | Raw password **never** appears in plugin output                |

---

## Deployment to AAP / AWX

1. **Install the Plugin Package on AWX/AAP nodes**
  - The package must be available in the AWX/AAP Python environment
  - For containerized deployments, build a custom **Execution Environment (EE)** that includes the plugin

2. **Register managed credential types**
  - Run `awx-manage setup_managed_credential_types`

3. **Create a Credential**
  - Use **Delinea Secret Server** managed credential type
   - Fill in `server_url`, `username`, `password`, and optionally `domain`

4. **Attach to Job Template**
   - The credential will be resolved at launch time
   - The token is injected as both env vars and extra vars

---

## Usage in Playbooks

Use the `delinea.ss.tss` lookup plugin with the injected token:

```yaml
- name: Retrieve a secret from Delinea Secret Server
  ansible.builtin.debug:
    msg: >-
      {{ lookup('delinea.ss.tss', 42,
                server_url=tss_server_url,
                token=tss_token) }}
```

Or via environment variables:

```yaml
- name: Use environment variables
  ansible.builtin.debug:
    msg: >-
      Server: {{ lookup('env', 'TSS_SERVER_URL') }}
      Token:  {{ lookup('env', 'TSS_TOKEN') }}
```

---

## Contributing / Future Work

- [ ] Add support for SDK-based authentication (client credentials grant)
- [ ] Add configurable `verify_ssl` toggle in the credential type input
- [ ] Add token caching to avoid re-authentication on rapid successive lookups
- [ ] Build and publish a custom Execution Environment image with the plugin pre-installed
- [ ] Add integration tests against a real Secret Server instance