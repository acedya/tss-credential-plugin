# Delinea Secret Server — AAP/AWX Credential Plugin

## Project Overview

Custom credential type and credential plugin for AAP/AWX integrating with Delinea Secret Server.

This plugin authenticates against Secret Server's OAuth2 endpoint, retrieves a short-lived access token, and injects it into the job runtime. The raw password is never exposed to the running job — only the token.

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

## Directory Structure

```
.
├── INSTRUCTIONS.md
├── Makefile
├── credential_plugins/
│   ├── __init__.py
│   └── delinea_secret_server.py
├── credential_type/
│   ├── credential_type_input.yaml
│   └── credential_type_injector_with_plugin.yaml
├── examples/
│   └── example_playbook.yaml
├── tests/
│   ├── __init__.py
│   └── test_delinea_credential_plugin.py
└── requirements.txt
```

## Credential Type Input Configuration

| Field | Type | Required | Secret | Description |
|-------|------|----------|--------|-------------|
| `server_url` | string | ✅ | No | Base URL (e.g. `https://myserver/SecretServer`) |
| `username` | string | ✅ | No | The (Application) user username |
| `password` | string | ✅ | ✅ | The corresponding password (encrypted at rest by AAP) |
| `domain` | string | No | No | The (Application) user domain |

## Injector Behavior

### Environment Variables

The following environment variables are injected into the job runtime:

- `TSS_SERVER_URL`: The Secret Server base URL
- `TSS_TOKEN`: The OAuth2 access token

### Extra Variables

The following extra variables are available in Ansible playbooks:

- `tss_server_url`: The Secret Server base URL
- `tss_token`: The OAuth2 access token

**Note:** The `password` field is **never** injected into the job runtime.

## Plugin Implementation Details

### Main Functions

#### `_get_access_token(server_url, username, password, domain=None, verify_ssl=True)`

Internal helper function that authenticates with Secret Server and returns an access token.

- **Parameters:**
  - `server_url` (str): Base URL of Secret Server
  - `username` (str): Username for authentication
  - `password` (str): Password for authentication
  - `domain` (str, optional): Domain for authentication
  - `verify_ssl` (bool, optional): Whether to verify SSL certificates (default: True)
  
- **Returns:** Access token (str)

- **Behavior:** 
  - POSTs to `{server_url}/oauth2/token` with `grant_type=password`
  - Raises `requests.HTTPError` on HTTP errors
  - Raises `KeyError` if response doesn't contain `access_token`

#### `backend(credential_params)`

Entry point for AWX/AAP credential plugin system.

- **Parameters:**
  - `credential_params` (dict): Dictionary containing credential fields from AAP/AWX
  
- **Returns:** Dictionary with `tss_token` and `tss_server_url` keys

## OAuth2 Token Request Format

The plugin makes the following HTTP request to authenticate:

```http
POST {server_url}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username={username}&password={password}&domain={domain}
```

**Response format:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1200
}
```

## Test Cases

The plugin includes comprehensive unit tests:

- `test_get_access_token_success`: Verifies successful token retrieval with domain
- `test_get_access_token_without_domain`: Verifies token retrieval without domain
- `test_get_access_token_http_error`: Verifies proper error handling for HTTP errors
- `test_get_access_token_missing_key`: Verifies error handling when `access_token` is missing
- `test_backend_returns_token_and_url`: Verifies the `backend()` function returns correct data
- `test_backend_password_not_in_output`: Security test ensuring password is not leaked

## Deployment Instructions for AAP/AWX

### 1. Create Custom Credential Type

1. Log into AAP/AWX as an administrator
2. Navigate to **Administration → Credential Types**
3. Click **Add**
4. Fill in:
   - **Name:** Delinea Secret Server
   - **Description:** OAuth2-based credential for Delinea Secret Server
5. **Input Configuration:** Paste contents from `credential_type/credential_type_input.yaml`
6. **Injector Configuration:** Paste contents from `credential_type/credential_type_injector_with_plugin.yaml`
7. Click **Save**

### 2. Install Plugin in Execution Environment

The credential plugin must be installed in the Execution Environment (EE) used by your job templates.

#### Option A: Add to existing EE

Create a `requirements.txt` with:
```
requests>=2.28.0
```

Copy the `credential_plugins/` directory to the EE's Python path (e.g., `/usr/local/lib/python3.x/site-packages/`).

#### Option B: Build custom EE

Create an `execution-environment.yml`:

```yaml
version: 1
build_arg_defaults:
  EE_BASE_IMAGE: 'quay.io/ansible/awx-ee:latest'

dependencies:
  python: requirements.txt
  
additional_build_steps:
  append:
    - COPY credential_plugins /usr/local/lib/python3/site-packages/credential_plugins
```

Build and publish:
```bash
ansible-builder build -t my-org/custom-ee:latest
podman push my-org/custom-ee:latest
```

### 3. Create Credential

1. Navigate to **Resources → Credentials**
2. Click **Add**
3. Fill in:
   - **Name:** My Secret Server Credential
   - **Credential Type:** Select "Delinea Secret Server" (the type you created)
   - **Server URL:** e.g., `https://mytenant.secretservercloud.com`
   - **Username:** Your application user username
   - **Password:** Your application user password
   - **Domain:** (optional) Your domain
4. Click **Save**

### 4. Attach to Job Template

1. Navigate to your Job Template
2. In the **Credentials** section, add the credential you created
3. Ensure the Job Template uses an Execution Environment that has the plugin installed
4. Save the template

## Usage Examples

### Using with delinea.ss.tss Lookup Plugin

#### Via Extra Variables

```yaml
---
- name: Retrieve a secret from Delinea Secret Server
  hosts: all
  gather_facts: false

  tasks:
    - name: Fetch secret by ID using injected token
      ansible.builtin.debug:
        msg: >-
          The secret value is:
          {{ lookup('delinea.ss.tss', 42,
                    server_url=tss_server_url,
                    token=tss_token) }}
```

#### Via Environment Variables

```yaml
---
- name: Retrieve a secret using environment variables
  hosts: all
  gather_facts: false

  tasks:
    - name: Fetch secret using environment variables
      ansible.builtin.debug:
        msg: >-
          The secret value is:
          {{ lookup('delinea.ss.tss', 42) }}
```

Note: When using environment variables, the `delinea.ss.tss` lookup plugin automatically reads `TSS_SERVER_URL` and `TSS_TOKEN` from the environment.

### Verifying Injected Variables

```yaml
---
- name: Verify credential injection
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Show injected extra variables
      ansible.builtin.debug:
        msg:
          - "Server URL: {{ tss_server_url }}"
          - "Token (first 20 chars): {{ tss_token[:20] }}..."

    - name: Show environment variables
      ansible.builtin.debug:
        msg:
          - "TSS_SERVER_URL: {{ lookup('env', 'TSS_SERVER_URL') }}"
          - "TSS_TOKEN: {{ lookup('env', 'TSS_TOKEN')[:20] }}..."
```

## Development and Testing

### Install Dependencies

```bash
make install
```

Or:

```bash
pip3 install -r requirements.txt
```

### Run Tests

```bash
make test
```

Or:

```bash
pytest tests/ -v
```

### Run Tests with Verbose Output

```bash
make test-verbose
```

### Lint Code

```bash
make lint
```

### Clean Build Artifacts

```bash
make clean
```

## Security Considerations

1. **Password Never Exposed:** The plugin ensures that the raw password is never injected into the job runtime. Only the short-lived OAuth2 token is provided.

2. **Token Lifetime:** The access token has a limited lifetime (typically 20 minutes by default in Secret Server). This reduces the window of exposure if the token is compromised.

3. **SSL Verification:** By default, SSL certificate verification is enabled. Only disable it in development/testing environments.

4. **Credential Storage:** AAP/AWX encrypts credentials at rest, so the password stored in the credential is protected.

## Future Work

- [ ] Add support for SDK-based authentication (client credentials grant)
- [ ] Add configurable `verify_ssl` toggle in the credential type input
- [ ] Add token caching to avoid re-authentication on rapid successive lookups
- [ ] Build and publish a custom Execution Environment image with the plugin pre-installed
- [ ] Add integration tests against a real Secret Server instance

## Troubleshooting

### "ModuleNotFoundError: No module named 'credential_plugins'"

The plugin is not installed in the Execution Environment. Ensure the `credential_plugins/` directory is in the Python path of your EE.

### "401 Unauthorized" or "invalid_grant" error

Check that:
- The username and password are correct
- The domain (if required) is correctly specified
- The user has appropriate permissions in Secret Server
- The application user account is not locked or disabled

### Token expires during job execution

The token lifetime is managed by Secret Server. If jobs are very long-running, consider:
- Increasing the token lifetime in Secret Server settings
- Implementing token refresh logic (future enhancement)

### SSL Certificate Verification Errors

If using self-signed certificates:
- Add the CA certificate to the EE's trust store
- Or set `verify_ssl=False` (not recommended for production)

## License

See repository license file.

## Support

For issues and questions, please open an issue in the GitHub repository.
