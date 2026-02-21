"""
Custom Credential Plugin for Delinea (Thycotic) Secret Server.

This plugin authenticates against Secret Server using the official Delinea
Python SDK (python-tss-sdk), retrieves a short-lived OAuth2 access token,
and returns the requested value (token or base_url) to AWX through
credential linking.

AWX calls backend(**kwargs) with all fields + metadata values as keyword
arguments.  The ``identifier`` metadata dropdown tells the plugin which
value to return.
"""

import collections
from typing import Any, Optional

from delinea.secrets.server import (
    DomainPasswordGrantAuthorizer,
    PasswordGrantAuthorizer,
)

# ── Input field definition (what the user fills in on the credential form) ──
#
# fields:    set once when the user creates a Delinea credential in AWX
# metadata:  set each time the user *links* a target credential field
#   - identifier dropdown selects the value to return ("token" or "base_url")
INPUTS = {
    "fields": [
        {
            "id": "base_url",
            "label": "Secret Server URL",
            "help_text": (
                "The base URL of Secret Server, e.g. "
                "https://myserver/SecretServer or "
                "https://mytenant.secretservercloud.com"
            ),
            "type": "string",
        },
        {
            "id": "username",
            "label": "Username",
            "help_text": "The (application) user username",
            "type": "string",
        },
        {
            "id": "domain",
            "label": "Domain",
            "help_text": "The (application) user domain (optional)",
            "type": "string",
        },
        {
            "id": "password",
            "label": "Password",
            "help_text": "The corresponding password",
            "type": "string",
            "secret": True,
        },
    ],
    "metadata": [
        {
            "id": "identifier",
            "label": "Output value",
            "type": "string",
            "choices": ["token", "base_url"],
            "default": "token",
            "help_text": (
                "Select which value to return: " "the OAuth2 token or the Secret Server base URL."
            ),
        },
    ],
    "required": ["base_url", "username", "password", "identifier"],
}


def _get_authorizer(
    base_url: str,
    username: str,
    password: str,
    domain: Optional[str] = None,
):
    """Create and return an authenticated Delinea SDK authorizer.

    Uses ``DomainPasswordGrantAuthorizer`` when *domain* is provided,
    otherwise ``PasswordGrantAuthorizer``.
    """
    if domain:
        return DomainPasswordGrantAuthorizer(base_url, username, domain, password)
    return PasswordGrantAuthorizer(base_url, username, password)


def backend(**kwargs: Any) -> str:
    """
    Called by AWX / AAP to resolve a credential value at job launch time.

    AWX passes all ``fields`` and ``metadata`` values as keyword arguments.
    The ``identifier`` kwarg (a dropdown defaulting to "token") selects
    which value to return:

    - ``token``    → OAuth2 access token (authenticates via the SDK)
    - ``base_url`` → the Secret Server base URL (pass-through)

    Returns
    -------
    str
        A single credential value.
    """
    base_url: str = kwargs["base_url"]
    username: str = kwargs["username"]
    password: str = kwargs["password"]
    domain: Optional[str] = kwargs.get("domain")
    identifier: str = kwargs.get("identifier", "token")

    if identifier == "base_url":
        return base_url

    if identifier == "token":
        authorizer = _get_authorizer(base_url, username, password, domain)
        token: str = authorizer.get_access_token()
        return token

    raise ValueError(f"Unknown identifier '{identifier}'. " f"Valid values: 'token', 'base_url'.")


# ── AWX Credential Plugin Definition ──────────────────────────────────────
# This namedtuple is discovered and registered by AWX via entry points.
CredentialPlugin = collections.namedtuple("CredentialPlugin", ["name", "inputs", "backend"])

delinea_secret_server = CredentialPlugin(
    name="Delinea Secret Server",
    inputs=INPUTS,
    backend=backend,
)
