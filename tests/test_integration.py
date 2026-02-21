"""
Integration tests — real calls to Delinea Secret Server.

These tests hit the live OAuth2 endpoint and require network access.
Run with:  make test-integration   (reads credentials from .env)
Manual:    pytest tests/test_integration.py -v -s

Required environment variables (see .env.example):
  TSS_BASE_URL, TSS_USERNAME, TSS_PASSWORD
Optional:
  TSS_DOMAIN
"""

import os
import traceback

import pytest
import requests

from credential_plugins.delinea_secret_server import _get_authorizer, backend

# ── Connection parameters (from environment) ────────────────────────────

BASE_URL = os.environ.get("TSS_BASE_URL", "")
DOMAIN = os.environ.get("TSS_DOMAIN", "")
USERNAME = os.environ.get("TSS_USERNAME", "")
PASSWORD = os.environ.get("TSS_PASSWORD", "")

_MISSING = [v for v in ("TSS_BASE_URL", "TSS_USERNAME", "TSS_PASSWORD") if not os.environ.get(v)]
if _MISSING:
    pytest.skip(
        f"Integration tests require env vars: {', '.join(_MISSING)}. "
        f"Copy .env.example to .env and run: make test-integration",
        allow_module_level=True,
    )


# ── Pre-flight HTTP diagnostics ─────────────────────────────────────────


def _diagnose_connectivity():
    """Hit health endpoints directly and print raw HTTP results."""
    print("\n=== Pre-flight connectivity diagnostics ===")
    print(f"  Base URL: {BASE_URL}")

    endpoints = [
        ("Secret Server healthcheck", "/api/v1/healthcheck"),
        ("Platform healthcheck", "/health"),
        ("OAuth2 token endpoint", "/oauth2/token"),
    ]

    for label, path in endpoints:
        url = BASE_URL.rstrip("/") + path
        print(f"\n  [{label}] GET {url}")
        try:
            r = requests.get(url, timeout=10)
            print(f"    Status : {r.status_code}")
            print(f"    Headers: {dict(r.headers)}")
            print(f"    Body   : {r.text[:500]}")
        except requests.exceptions.SSLError as e:
            print(f"    SSL ERROR: {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"    CONNECTION ERROR: {e}")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")

    # Also try with verify=False to isolate SSL vs server issues
    print(f"\n  [SSL bypass test] GET {BASE_URL}/api/v1/healthcheck (verify=False)")
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(BASE_URL.rstrip("/") + "/api/v1/healthcheck", timeout=10)
        print(f"    Status : {r.status_code}")
        print(f"    Body   : {r.text[:500]}")
    except Exception as e:
        print(f"    ERROR: {type(e).__name__}: {e}")

    print("\n=== End diagnostics ===\n")


# ── Helpers ──────────────────────────────────────────────────────────────


def _try_get_token(label=""):
    """Attempt to get an access token; print full diagnostics on failure."""
    prefix = f"[{label}] " if label else ""
    print(f"\n{prefix}Attempting OAuth2 login...")
    print(f"{prefix}  base_url : {BASE_URL}")
    print(f"{prefix}  username : {USERNAME}")
    print(f"{prefix}  domain   : {DOMAIN}")
    try:
        auth = _get_authorizer(BASE_URL, USERNAME, PASSWORD, domain=DOMAIN)
        print(f"{prefix}  Authorizer created: {type(auth).__name__}")
        token = auth.get_access_token()
        print(f"{prefix}  Token obtained (length={len(token)}): {token[:40]}...")
        return token
    except Exception as exc:
        print(f"{prefix}  ERROR: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise


@pytest.fixture(scope="module")
def authorizer():
    """Return a live authorizer; skip the whole module if unreachable."""
    try:
        auth = _get_authorizer(BASE_URL, USERNAME, PASSWORD, domain=DOMAIN)
        _ = auth.get_access_token()
        return auth
    except Exception as exc:
        print(f"\n[fixture] Cannot reach Secret Server: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        pytest.skip(f"Cannot reach Secret Server: {exc}")


# ── Tests ────────────────────────────────────────────────────────────────


class TestGetAuthorizer:
    """Verify _get_authorizer with real credentials."""

    def test_authorizer_returns_token(self, authorizer):
        """OAuth2 token is a non-empty string."""
        token = authorizer.get_access_token()
        print(f"\n  Token (first 40 chars): {token[:40]}...")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_looks_like_jwt_or_opaque(self, authorizer):
        """Token should be a reasonably long opaque or JWT string."""
        token = authorizer.get_access_token()
        print(f"\n  Token length: {len(token)}, dot count: {token.count('.')}")
        # JWTs have 3 dot-separated parts; opaque tokens are typically 20+ chars
        assert len(token) >= 20 or token.count(".") == 2


class TestBackend:
    """Verify the AWX backend() entry point with real credentials."""

    def test_backend_token(self):
        """backend() returns a non-empty token string."""
        try:
            result = backend(
                base_url=BASE_URL,
                username=USERNAME,
                password=PASSWORD,
                domain=DOMAIN,
                identifier="token",
            )
            print(
                f"\n  backend(identifier='token') returned (length={len(result)}): {result[:40]}..."
            )
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as exc:
            print(f"\n  backend(identifier='token') FAILED: {type(exc).__name__}: {exc}")
            _diagnose_connectivity()
            traceback.print_exc()
            raise

    def test_backend_base_url(self):
        """backend() returns the base URL when identifier='base_url'."""
        result = backend(
            base_url=BASE_URL,
            username=USERNAME,
            password=PASSWORD,
            domain=DOMAIN,
            identifier="base_url",
        )
        print(f"\n  backend(identifier='base_url') returned: {result}")
        assert result == BASE_URL

    def test_backend_password_never_returned(self):
        """The raw password must never appear in the token output."""
        try:
            token = backend(
                base_url=BASE_URL,
                username=USERNAME,
                password=PASSWORD,
                domain=DOMAIN,
                identifier="token",
            )
            print("\n  Token obtained, verifying password is not in output...")
            assert PASSWORD not in token
        except Exception as exc:
            print(f"\n  backend() FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            raise

    def test_backend_default_identifier_is_token(self):
        """Omitting identifier defaults to 'token' and returns a valid value."""
        try:
            result = backend(
                base_url=BASE_URL,
                username=USERNAME,
                password=PASSWORD,
                domain=DOMAIN,
            )
            print(f"\n  backend(no identifier) returned (length={len(result)}): {result[:40]}...")
            assert isinstance(result, str)
            assert len(result) > 0
            assert result != BASE_URL  # should be the token, not the URL
        except Exception as exc:
            print(f"\n  backend(no identifier) FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()
            raise
