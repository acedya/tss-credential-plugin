"""Unit tests for the Delinea Secret Server credential plugin."""

import sys
from unittest.mock import MagicMock, patch

import pytest

import credential_plugins.delinea_secret_server  # noqa: F401
from credential_plugins.delinea_secret_server import (
    INPUTS,
    _get_authorizer,
    backend,
    delinea_secret_server,
)

# The __init__.py re-export shadows the module name on the package object,
# so ``import credential_plugins.delinea_secret_server as mod`` returns the
# CredentialPlugin namedtuple.  Grab the real module from sys.modules.
_plugin_mod = sys.modules["credential_plugins.delinea_secret_server"]

FAKE_SERVER = "https://myserver.example.com/SecretServer"
FAKE_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.fakepayload.fakesig"


# ── _get_authorizer tests ───────────────────────────────────────────────


@patch.object(_plugin_mod, "PasswordGrantAuthorizer")
def test_get_authorizer_without_domain(mock_cls):
    """Uses PasswordGrantAuthorizer when domain is not provided."""
    _get_authorizer(FAKE_SERVER, "appuser", "s3cret")
    mock_cls.assert_called_once_with(FAKE_SERVER, "appuser", "s3cret")


@patch.object(_plugin_mod, "DomainPasswordGrantAuthorizer")
def test_get_authorizer_with_domain(mock_cls):
    """Uses DomainPasswordGrantAuthorizer when domain is provided."""
    _get_authorizer(FAKE_SERVER, "appuser", "s3cret", domain="MYDOMAIN")
    mock_cls.assert_called_once_with(FAKE_SERVER, "appuser", "MYDOMAIN", "s3cret")


# ── backend() tests ─────────────────────────────────────────────────────


@patch.object(_plugin_mod, "PasswordGrantAuthorizer")
def test_backend_returns_token(mock_cls):
    """backend() returns the OAuth2 token when identifier is 'token'."""
    mock_cls.return_value = MagicMock(token=FAKE_TOKEN)

    result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        identifier="token",
    )

    assert result == FAKE_TOKEN
    assert isinstance(result, str)


@patch.object(_plugin_mod, "PasswordGrantAuthorizer")
def test_backend_defaults_to_token(mock_cls):
    """backend() defaults to 'token' when identifier is not specified."""
    mock_cls.return_value = MagicMock(token=FAKE_TOKEN)

    result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
    )

    assert result == FAKE_TOKEN


@patch.object(_plugin_mod, "DomainPasswordGrantAuthorizer")
def test_backend_token_with_domain(mock_cls):
    """backend() uses DomainPasswordGrantAuthorizer when domain is provided."""
    mock_cls.return_value = MagicMock(token=FAKE_TOKEN)

    result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        domain="CORP",
        identifier="token",
    )

    assert result == FAKE_TOKEN
    mock_cls.assert_called_once_with(FAKE_SERVER, "appuser", "CORP", "s3cret")


def test_backend_returns_base_url():
    """backend() returns the base_url when identifier is 'base_url'."""
    result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        identifier="base_url",
    )

    assert result == FAKE_SERVER
    assert isinstance(result, str)


def test_backend_raises_on_unknown_identifier():
    """backend() raises ValueError for an unrecognised identifier."""
    with pytest.raises(ValueError, match="Unknown identifier"):
        backend(
            base_url=FAKE_SERVER,
            username="appuser",
            password="s3cret",
            identifier="unknown_key",
        )


@patch.object(_plugin_mod, "PasswordGrantAuthorizer")
def test_backend_password_not_in_output(mock_cls):
    """The raw password must NEVER appear in the plugin output."""
    mock_cls.return_value = MagicMock(token=FAKE_TOKEN)

    token_result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        identifier="token",
    )
    url_result = backend(
        base_url=FAKE_SERVER,
        username="appuser",
        password="s3cret",
        identifier="base_url",
    )

    assert "s3cret" not in token_result
    assert "s3cret" not in url_result


@patch.object(_plugin_mod, "PasswordGrantAuthorizer")
def test_backend_sdk_error_propagates(mock_cls):
    """SDK authentication errors propagate to AWX."""
    mock_cls.side_effect = Exception("Authentication failed")

    with pytest.raises(Exception, match="Authentication failed"):
        backend(
            base_url=FAKE_SERVER,
            username="wrong",
            password="wrong",
            identifier="token",
        )


# ── INPUTS schema tests ─────────────────────────────────────────────────


def test_inputs_has_required_fields():
    """INPUTS must declare the expected authentication fields."""
    field_ids = {f["id"] for f in INPUTS["fields"]}
    assert {"base_url", "username", "password", "domain"} == field_ids


def test_inputs_password_is_secret():
    """The password field must be marked as secret."""
    pw_field = next(f for f in INPUTS["fields"] if f["id"] == "password")
    assert pw_field.get("secret") is True


def test_inputs_metadata_has_identifier():
    """INPUTS metadata must include an 'identifier' field."""
    metadata = INPUTS.get("metadata")
    assert metadata is not None, "INPUTS must include a 'metadata' array"
    metadata_ids = {m["id"] for m in metadata}
    assert "identifier" in metadata_ids


def test_inputs_identifier_has_choices():
    """The identifier metadata field must have choices (not free-text)."""
    identifier = next(m for m in INPUTS["metadata"] if m["id"] == "identifier")
    assert "choices" in identifier
    assert "token" in identifier["choices"]
    assert "base_url" in identifier["choices"]


def test_inputs_identifier_has_default():
    """The identifier metadata field must default to 'token'."""
    identifier = next(m for m in INPUTS["metadata"] if m["id"] == "identifier")
    assert identifier.get("default") == "token"


def test_inputs_required_includes_identifier():
    """The identifier metadata field must be listed as required."""
    assert "identifier" in INPUTS["required"]


# ── CredentialPlugin namedtuple tests ────────────────────────────────────


def test_credential_plugin_structure():
    """The CredentialPlugin namedtuple has exactly three fields: name, inputs, backend."""
    assert hasattr(delinea_secret_server, "name")
    assert hasattr(delinea_secret_server, "inputs")
    assert hasattr(delinea_secret_server, "backend")
    assert len(delinea_secret_server) == 3


def test_credential_plugin_no_injectors():
    """AWX credential plugins do NOT include injectors (AWX handles injection)."""
    assert not hasattr(delinea_secret_server, "injectors")


def test_credential_plugin_name():
    """The plugin name matches what AWX displays in the UI."""
    assert delinea_secret_server.name == "Delinea Secret Server"


def test_credential_plugin_inputs_is_inputs():
    """The plugin inputs reference the module-level INPUTS dict."""
    assert delinea_secret_server.inputs is INPUTS


def test_credential_plugin_backend_is_callable():
    """The plugin backend is the module-level backend function."""
    assert delinea_secret_server.backend is backend
    assert callable(delinea_secret_server.backend)
