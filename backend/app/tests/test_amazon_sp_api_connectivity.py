from __future__ import annotations

import os

import pytest

from app.core.config import Settings
from app.integrations.amazon_sp_api import AmazonSpApiClient


@pytest.mark.integration
def test_amazon_sp_api_connectivity() -> None:
    if os.getenv("AMAZON_SP_API_CONNECTIVITY_TEST") != "1":
        pytest.skip("Set AMAZON_SP_API_CONNECTIVITY_TEST=1 to call Amazon SP-API.")

    settings = Settings()
    missing = [
        name
        for name, value in {
            "AMAZON_LWA_CLIENT_ID": settings.amazon_lwa_client_id,
            "AMAZON_LWA_CLIENT_SECRET": settings.amazon_lwa_client_secret,
            "AMAZON_REFRESH_TOKEN": settings.amazon_refresh_token,
            "AMAZON_MARKETPLACE_ID": settings.amazon_marketplace_id,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip(f"Missing Amazon SP-API env vars: {', '.join(missing)}")

    with AmazonSpApiClient(settings) as client:
        access_token = client.get_access_token()
        payload = client.get_marketplace_participations()

    assert access_token.startswith("Atza|")
    assert isinstance(payload, dict)
