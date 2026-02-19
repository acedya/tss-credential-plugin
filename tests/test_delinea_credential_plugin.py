"""Unit tests for the Delinea Secret Server credential plugin."""

import json

import pytest
import responses

from credential_plugins.delinea_secret_server import (
    TOKEN_ENDPOINT,
    _get_access_token,
    backend,
)

FAKE_SERVER = "https://myserver.example.com/SecretServer"
FAKE_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.fakepayload.fakesig"


@responses.activate
def test_get_access_token_success():
    """Token is returned on a successful OAuth2 call."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"access_token": FAKE_TOKEN, "token_type": "bearer", "expires_in": 1200},
        status=200,
    )

    token = _get_access_token(
        server_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        domain="MYDOMAIN",
    )
    assert token == FAKE_TOKEN

    # Verify the POST body
    body = responses.calls[0].request.body
    assert "grant_type=password" in body
    assert "username=appuser" in body
    assert "domain=MYDOMAIN" in body


@responses.activate
def test_get_access_token_without_domain():
    """Domain is optional and should not appear in the request if absent."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"access_token": FAKE_TOKEN},
        status=200,
    )

    _get_access_token(
        server_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
    )

    body = responses.calls[0].request.body
    assert "domain" not in body


@responses.activate
def test_get_access_token_http_error():
    """HTTPError is raised on non-2xx responses."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"error": "invalid_grant"},
        status=400,
    )

    with pytest.raises(Exception):
        _get_access_token(
            server_url=FAKE_SERVER,
            username="wrong",
            password="wrong",
        )


@responses.activate
def test_get_access_token_missing_key():
    """KeyError is raised when access_token is missing from the response."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"token_type": "bearer"},
        status=200,
    )

    with pytest.raises(KeyError, match="access_token"):
        _get_access_token(
            server_url=FAKE_SERVER,
            username="appuser",
            password="s3cret",
        )


@responses.activate
def test_backend_returns_token_and_url():
    """The backend() function returns the expected dict for AWX injection."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"access_token": FAKE_TOKEN},
        status=200,
    )

    result = backend(
        {
            "server_url": FAKE_SERVER,
            "username": "appuser",
            "password": "s3cret",
            "domain": "CORP",
        }
    )

    assert result == {
        "tss_token": FAKE_TOKEN,
        "tss_server_url": FAKE_SERVER,
    }


@responses.activate
def test_backend_password_not_in_output():
    """The raw password must NEVER appear in the plugin output."""
    responses.add(
        responses.POST,
        FAKE_SERVER + TOKEN_ENDPOINT,
        json={"access_token": FAKE_TOKEN},
        status=200,
    )

    result = backend(
        {
            "server_url": FAKE_SERVER,
            "username": "appuser",
            "password": "s3cret",
        }
    )

    output_str = json.dumps(result)
    assert "s3cret" not in output_str
