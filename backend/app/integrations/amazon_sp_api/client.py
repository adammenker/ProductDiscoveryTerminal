from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from threading import Lock
from time import monotonic, sleep
from typing import Any

import httpx

_RATE_LIMIT_LOCK = Lock()
_NEXT_REQUEST_AT: dict[str, float] = {}


class AmazonSpApiError(RuntimeError):
    pass


class AmazonSpApiAuthenticationError(AmazonSpApiError):
    pass


class AmazonSpApiRequestError(AmazonSpApiError):
    pass


class AmazonSpApiClient:
    def __init__(self, settings: Any, http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self._http_client = http_client
        self._access_token: str | None = None
        self._access_token_expires_at = 0.0
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._http_client is not None and self._owns_client:
            self._http_client.close()

    def __enter__(self) -> AmazonSpApiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_access_token(self) -> str:
        if self._access_token and monotonic() < self._access_token_expires_at:
            return self._access_token

        client = self._client()
        response = client.post(
            self.settings.amazon_lwa_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.settings.amazon_refresh_token,
                "client_id": self.settings.amazon_lwa_client_id,
                "client_secret": self.settings.amazon_lwa_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AmazonSpApiAuthenticationError(
                f"Amazon LWA token exchange failed with HTTP {exc.response.status_code}."
            ) from exc

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise AmazonSpApiAuthenticationError(
                "Amazon LWA token exchange response did not include access_token."
            )
        self._access_token = str(access_token)
        expires_in = max(60, int(payload.get("expires_in") or 3600))
        self._access_token_expires_at = monotonic() + expires_in - 60
        return self._access_token

    def get_catalog_items(self, keywords: str, page_size: int = 10) -> dict[str, Any]:
        params = {
            "marketplaceIds": self.settings.amazon_marketplace_id,
            "keywords": keywords,
            "pageSize": max(1, min(page_size, 20)),
            "includedData": "summaries,images,salesRanks",
        }
        return self.get("/catalog/2022-04-01/items", params=params)

    def get_marketplace_participations(self) -> dict[str, Any]:
        return self.get("/sellers/v1/marketplaceParticipations")

    def get_competitive_pricing_for_asin(self, asin: str) -> dict[str, Any]:
        params = {
            "MarketplaceId": self.settings.amazon_marketplace_id,
            "Asins": asin,
            "ItemType": "Asin",
        }
        return self.get("/products/pricing/v0/competitivePrice", params=params)

    def get_fees_estimate_for_asin(self, asin: str, listing_price: float) -> dict[str, Any]:
        body = {
            "FeesEstimateRequest": {
                "MarketplaceId": self.settings.amazon_marketplace_id,
                "IsAmazonFulfilled": True,
                "PriceToEstimateFees": {
                    "ListingPrice": {"CurrencyCode": "USD", "Amount": listing_price}
                },
                "Identifier": f"{asin}:{listing_price}",
            }
        }
        return self.post(f"/products/fees/v0/items/{asin}/feesEstimate", json=body)

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(
            "GET",
            path,
            params=params,
        )
        return self._json_response(response)

    def post(
        self,
        path: str,
        json: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request(
            "POST",
            path,
            json=json,
        )
        return self._json_response(response)

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        attempts = max(1, int(self.settings.amazon_request_max_attempts))
        response: httpx.Response | None = None
        for attempt in range(attempts):
            operation = self._operation(path)
            self._wait_for_rate_limit(operation)
            try:
                response = self._client().request(
                    method,
                    f"{self._endpoint()}/{path.lstrip('/')}",
                    headers=self._sp_api_headers(),
                    **kwargs,
                )
            except httpx.TransportError as exc:
                if attempt + 1 >= attempts:
                    raise AmazonSpApiRequestError(
                        f"Amazon SP-API {operation} request failed after {attempts} attempts."
                    ) from exc
                sleep(self._retry_delay(None, attempt))
                continue
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            if attempt + 1 < attempts:
                delay = self._retry_delay(response, attempt)
                self._defer_operation(operation, delay)
                sleep(delay)
        assert response is not None
        return response

    def _operation(self, path: str) -> str:
        if path.startswith("/catalog/"):
            return "catalog"
        if path.startswith("/products/pricing/"):
            return "pricing"
        if path.startswith("/products/fees/"):
            return "fees"
        return "default"

    def _request_interval(self, operation: str) -> float:
        setting = {
            "catalog": "amazon_catalog_request_interval_seconds",
            "pricing": "amazon_pricing_request_interval_seconds",
            "fees": "amazon_fees_request_interval_seconds",
        }.get(operation)
        return max(0.0, float(getattr(self.settings, setting, 0.0))) if setting else 0.0

    def _wait_for_rate_limit(self, operation: str) -> None:
        interval = self._request_interval(operation)
        if interval <= 0:
            return
        with _RATE_LIMIT_LOCK:
            now = monotonic()
            request_at = max(now, _NEXT_REQUEST_AT.get(operation, now))
            _NEXT_REQUEST_AT[operation] = request_at + interval
        sleep(max(0.0, request_at - monotonic()))

    @staticmethod
    def _defer_operation(operation: str, delay: float) -> None:
        with _RATE_LIMIT_LOCK:
            _NEXT_REQUEST_AT[operation] = max(
                _NEXT_REQUEST_AT.get(operation, 0.0),
                monotonic() + delay,
            )

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        delay = _parse_retry_after(retry_after)
        if delay is None or delay <= 0:
            delay = float(self.settings.amazon_request_backoff_seconds) * (2**attempt)
        return max(0.0, delay)

    def _sp_api_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "User-Agent": self.settings.amazon_user_agent,
            "x-amz-access-token": self.get_access_token(),
            "x-amz-date": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        }

    def _endpoint(self) -> str:
        configured_endpoint = self.settings.amazon_sp_api_endpoint
        if configured_endpoint:
            return str(configured_endpoint).rstrip("/")
        environment = str(self.settings.amazon_sp_api_environment).lower()
        if environment == "production":
            return str(self.settings.amazon_sp_api_endpoint_production).rstrip("/")
        return str(self.settings.amazon_sp_api_endpoint_sandbox).rstrip("/")

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self.settings.amazon_request_timeout_seconds)
        return self._http_client

    @staticmethod
    def _json_response(response: httpx.Response) -> dict[str, Any]:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AmazonSpApiRequestError(
                f"Amazon SP-API request failed with HTTP {exc.response.status_code}."
            ) from exc
        payload = response.json()
        return payload if isinstance(payload, dict) else {"payload": payload}


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None
