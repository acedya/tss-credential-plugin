# Delinea Secret Server AWX Credential Plugin

Custom AWX/AAP managed credential plugin for Delinea (Thycotic) Secret Server.

## Do I need `credential_type` YAML files?

No, not for the managed plugin itself.

This package follows the AWX custom credential plugin pattern:
- it exposes a `CredentialPlugin` object through Python entry points;
- input schema is defined in Python (`inputs`);
- AWX discovers and registers it using `awx-manage setup_managed_credential_types`.

The `credential_type/` YAML files can be kept only as reference/manual fallback, but they are not required for plugin operation.

## Install

```bash
pip install awx-delinea-secret-server-credential-plugin
```

Then on AWX node(s):

```bash
awx-manage setup_managed_credential_types
```

## Development

```bash
make install-dev
make test
```

## Makefile as source of truth

Workflows call Makefile targets so local and CI behavior stay aligned.

- `make format` → applies `black` + `isort`
- `make lint` → CI-equivalent lint checks (`black --check`, `isort --check-only`, `flake8`, `mypy`, syntax check)
- `make test-ci` → CI-equivalent tests with coverage XML output
- `make build` → creates `dist/` artifacts
- `make release-check` → build + `twine check`
- `make ci` → full CI-equivalent run (`lint`, `test-ci`, `build`)
- `make release-tag TAG=vX.Y.Z [PUSH=1]` → runs `make ci`, creates annotated tag, optionally pushes it

Local release fallback (token-based) is available if needed:

- `make publish-testpypi-token TEST_PYPI_API_TOKEN=...`
- `make publish-pypi-token PYPI_API_TOKEN=...`

Production GitHub publishing still uses OIDC Trusted Publishing in workflows.

## Safe release tagging

Use the helper to avoid accidental bad tags:

```bash
# Validate + run CI-equivalent checks + create local tag
make release-tag TAG=v0.2.1

# Validate + run checks + create and push tag
make release-tag TAG=v0.2.1 PUSH=1
```

Safety checks performed by `scripts/release.sh`:
- strict tag format validation (`vX.Y.Z`)
- clean git working tree required
- tag must not already exist locally or on `origin`
- mandatory `make ci` before tag creation

## GitHub Trusted Publishing (recommended)

This repository uses PyPI Trusted Publishing via GitHub OIDC, so no API token secrets are required.

Create two publishing configurations:
- On PyPI for project `awx-delinea-secret-server-credential-plugin`
- On TestPyPI for the same project name

Use these values in both PyPI and TestPyPI trusted publisher settings:
- Owner: your GitHub org/user
- Repository: `tss-credential-plugin`
- Workflow: `release.yml`
- Environment: `pypi` (for production), `testpypi` (for TestPyPI)

Publish triggers:
- TestPyPI: pushes to `develop` via `release.yml`
- PyPI + GitHub Release: strict semantic tags `vX.Y.Z` (example: `v0.2.0`) via `release.yml`

CI checks (tests/lint/build validation) run in `ci.yml` on `main`, `develop`, and pull requests.

Release notes are populated from `CHANGELOG.md`.
