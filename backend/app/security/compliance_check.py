from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings

REQUIRED_DOCS = {
    "incident_response_doc_exists": "INCIDENT_RESPONSE.md",
    "network_security_doc_exists": "NETWORK_SECURITY.md",
    "access_control_doc_exists": "ACCESS_CONTROL.md",
    "credential_management_doc_exists": "CREDENTIAL_MANAGEMENT.md",
    "amazon_data_handling_doc_exists": "AMAZON_DATA_HANDLING.md",
    "security_doc_exists": "SECURITY.md",
    "review_log_exists": "REVIEW_LOG.md",
}

AMAZON_CREDENTIAL_FIELDS = {
    "AMAZON_LWA_CLIENT_ID": "amazon_lwa_client_id",
    "AMAZON_LWA_CLIENT_SECRET": "amazon_lwa_client_secret",
    "AMAZON_LWA_REFRESH_TOKEN": "amazon_refresh_token",
    "AMAZON_MARKETPLACE_ID": "amazon_marketplace_id",
}


def compliance_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    compliance_dir = find_compliance_dir(settings)
    missing_credentials = [
        env_name
        for env_name, field_name in AMAZON_CREDENTIAL_FIELDS.items()
        if not getattr(settings, field_name)
    ]

    status: dict[str, Any] = {
        "app_env": settings.app_env,
        "amazon_spapi_env": settings.amazon_sp_api_environment,
        "amazon_credentials_configured": not missing_credentials,
        "amazon_missing_credentials": missing_credentials,
        "allow_public_unauthenticated": settings.allow_public_unauthenticated,
        "production_guard_enabled": True,
        "public_url_https": _public_url_https(settings.public_app_url),
        "compliance_docs_path": str(compliance_dir),
        "secrets_redaction_enabled": True,
    }
    status.update(
        {
            key: (compliance_dir / filename).exists()
            for key, filename in REQUIRED_DOCS.items()
        }
    )
    return status


def find_compliance_dir(settings: Settings) -> Path:
    configured = Path(settings.compliance_docs_path).expanduser()
    candidates = [
        configured,
        Path.cwd().parent / "compliance",
        Path(__file__).resolve().parents[3] / "compliance",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return configured


def _public_url_https(public_url: str | None) -> bool | None:
    if not public_url:
        return None
    return public_url.startswith("https://")


def main() -> None:
    print(json.dumps(compliance_status(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

