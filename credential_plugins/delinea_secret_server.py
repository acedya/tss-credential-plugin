"""
Custom Credential Plugin for Delinea (Thycotic) Secret Server.

This plugin authenticates against Secret Server's OAuth2 endpoint,
retrieves an access token, and injects it into the job runtime
as environment variables and extra vars for use with the
delinea.ss.tss Ansible lookup plugin.
"""

import requests
from typing import Any, Dict, Optional


PLUGIN_NAME = "delinea_secret_server"
PLUGIN_DESCRIPTION = (
    "Authenticate to Delinea Secret Server and inject an OAuth2 token "
    "for use with the delinea.ss.tss lookup plugin."
)

INPUTS = {
    "fields": [
        {
            "id": "server_url",
            "label": "Secret Server URL",
            "help_text": (
                "The Base URL of Secret Server e.g. "
                "https://myserver/SecretServer or "
                "https://mytenant.secretservercloud.com"
            ),
            "type": "string",
        },
        {
            "id": "username",
            "label": "Username",
            "help_text": "The (Application) user username",
            "type": "string",
        },
        {
            "id": "domain",
            "label": "Domain",
            "help_text": "The (Application) user domain",
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
    "required": ["server_url", "username", "password"],
}

TOKEN_ENDPOINT = "/oauth2/token"


def _get_access_token(
    server_url: str,
    username: str,
    password: str,
    domain: Optional[str] = None,
    verify_ssl: bool = True,
) -> str:
    token_url = server_url.rstrip("/") + TOKEN_ENDPOINT

    payload: Dict[str, str] = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }
    if domain:
        payload["domain"] = domain

    response = requests.post(
        token_url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        verify=verify_ssl,
    )
    response.raise_for_status()

    data = response.json()
    if "access_token" not in data:
        raise KeyError(
            f"Secret Server token response did not contain 'access_token'. "
            f"Response keys: {list(data.keys())}"
        )

    return data["access_token"]


def backend(credential_params: Dict[str, Any]) -> Dict[str, str]:
    server_url: str = credential_params["server_url"]
    username: str = credential_params["username"]
    password: str = credential_params["password"]
    domain: Optional[str] = credential_params.get("domain")

    token = _get_access_token(
        server_url=server_url,
        username=username,
        password=password,
        domain=domain,
    )

    return {
        "tss_token": token,
        "tss_server_url": server_url,
    }
