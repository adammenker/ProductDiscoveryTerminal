from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.integrations.amazon_sp_api import AmazonSpApiClient
from app.pipeline.runner import PipelineRunner
from app.schemas.plugin import IngestionQuery, PipelineRunRequest
from app.security.compliance_check import compliance_status
from app.security.redaction import REDACTED, redact_sensitive
from app.security.runtime import validate_runtime_security

REPO_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[3]))
COMPLIANCE_DIR = REPO_ROOT / "compliance"


def test_required_compliance_documents_exist_and_cover_flagged_controls() -> None:
    required = {
        "README.md",
        "SECURITY.md",
        "ACCESS_CONTROL.md",
        "INCIDENT_RESPONSE.md",
        "NETWORK_SECURITY.md",
        "CREDENTIAL_MANAGEMENT.md",
        "AMAZON_DATA_HANDLING.md",
        "REVIEW_LOG.md",
        "AMAZON_DEVELOPER_PROFILE_RESPONSES.md",
    }

    assert required.issubset({path.name for path in COMPLIANCE_DIR.iterdir()})

    incident_response = (COMPLIANCE_DIR / "INCIDENT_RESPONSE.md").read_text()
    access_control = (COMPLIANCE_DIR / "ACCESS_CONTROL.md").read_text()
    network_security = (COMPLIANCE_DIR / "NETWORK_SECURITY.md").read_text()

    assert "security@amazon.com" in incident_response
    assert "24 hours" in incident_response
    assert "6 months" in incident_response
    assert "12 characters" in access_control
    assert "Special characters" in access_control
    assert "MFA" in access_control
    assert "365 days" in access_control
    for term in ("firewall", "IDS/IPS", "anti-virus", "anti-malware", "segmentation"):
        assert term.lower() in network_security.lower()


def test_env_example_contains_placeholders_only_and_env_files_are_ignored() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text()
    gitignore = (REPO_ROOT / ".gitignore").read_text()

    assert "AMAZON_LWA_CLIENT_SECRET=replace_me" in env_example
    assert "AMAZON_LWA_REFRESH_TOKEN=replace_me" in env_example
    assert "Atzr|" not in env_example
    assert "Atza|" not in env_example
    assert "amzn1.oa2-cs" not in env_example
    assert "\n.env\n" in f"\n{gitignore}\n"
    assert "\n.env.*\n" in f"\n{gitignore}\n"
    assert "\n!.env.example\n" in f"\n{gitignore}\n"


def test_secret_redaction_handles_nested_data_and_strings() -> None:
    value = {
        "headers": {
            "authorization": "Bearer Atza|access-token-value",
            "x-amz-access-token": "Atza|another-token",
        },
        "client_secret": "amzn1.oa2-cs.v1.example",
        "message": "refresh_token=Atzr|refresh-token-value",
        "safe": "catalog",
    }

    redacted = redact_sensitive(value)

    assert redacted["headers"]["authorization"] == REDACTED
    assert redacted["headers"]["x-amz-access-token"] == REDACTED
    assert redacted["client_secret"] == REDACTED
    assert "Atzr|" not in redacted["message"]
    assert redacted["safe"] == "catalog"


def test_compliance_status_endpoint_exposes_no_secret_values(client: TestClient) -> None:
    response = client.get("/security/compliance-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident_response_doc_exists"] is True
    assert payload["network_security_doc_exists"] is True
    assert payload["credential_management_doc_exists"] is True
    rendered = str(payload)
    assert "secret" not in rendered.lower() or "missing_credentials" in rendered
    assert "Atzr|" not in rendered
    assert "Atza|" not in rendered
    assert "amzn1.oa2-cs" not in rendered


def test_compliance_status_reports_configured_without_exposing_credentials() -> None:
    settings = Settings(
        amazon_sp_api_environment="production",
        amazon_lwa_client_id="amzn1.application-oa2-client.example",
        amazon_lwa_client_secret="amzn1.oa2-cs.v1.example",
        amazon_refresh_token="Atzr|refresh-token-value",
        amazon_marketplace_id="ATVPDKIKX0DER",
        compliance_docs_path=str(COMPLIANCE_DIR),
    )

    payload = compliance_status(settings)
    rendered = str(payload)

    assert payload["amazon_spapi_env"] == "production"
    assert payload["amazon_credentials_configured"] is True
    assert payload["amazon_missing_credentials"] == []
    assert "Atzr|" not in rendered
    assert "amzn1.oa2-cs" not in rendered


def test_runtime_security_fails_fast_for_unauthenticated_production() -> None:
    settings = Settings(app_env="production", allow_public_unauthenticated=False)

    with pytest.raises(RuntimeError, match="APP_ENV=production"):
        validate_runtime_security(settings)


def test_amazon_sp_api_environment_selects_expected_endpoint() -> None:
    sandbox = AmazonSpApiClient(Settings(amazon_sp_api_environment="sandbox"))
    production = AmazonSpApiClient(Settings(amazon_sp_api_environment="production"))

    assert sandbox._endpoint() == "https://sandbox.sellingpartnerapi-na.amazon.com"
    assert production._endpoint() == "https://sellingpartnerapi-na.amazon.com"


def test_amazon_plugin_failure_is_captured_by_pipeline(db_session) -> None:  # type: ignore[no-untyped-def]
    result = PipelineRunner(db_session).run(
        PipelineRunRequest(
            plugins=["amazon_catalog_spapi"],
            query=IngestionQuery(query="ice roller", limit=1),
            run_analyzers=False,
            score=False,
        )
    )

    assert result.status == "failed"
    assert result.plugin_runs[0].plugin_name == "amazon_catalog_spapi"
    assert result.plugin_runs[0].status == "failed"
    assert "amazon_catalog_spapi is disabled" in result.errors[0]
