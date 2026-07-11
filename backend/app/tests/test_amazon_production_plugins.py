from __future__ import annotations

from typing import Any

import pytest

from app.core.config import Settings
from app.plugins.analyzers.amazon_comparable_asins import AmazonComparableAsinsAnalyzer
from app.plugins.analyzers.review.plugin import ReviewAnalyzer
from app.plugins.analyzers.risk.plugin import RiskAnalyzer
from app.plugins.ingestion.amazon_catalog_spapi import AmazonCatalogSpApiPlugin
from app.plugins.ingestion.amazon_fees_spapi import AmazonFeesSpApiPlugin
from app.plugins.ingestion.amazon_pricing_spapi import AmazonPricingSpApiPlugin
from app.schemas.plugin import IngestionQuery, ProductContext, RawObservationDTO


def _amazon_settings(**overrides: Any) -> Settings:
    settings = Settings(
        _env_file=None,
        amazon_sp_api_enabled=True,
        amazon_lwa_client_id="client-id",
        amazon_lwa_client_secret="client-secret",
        amazon_refresh_token="refresh-token",
        amazon_marketplace_id="ATVPDKIKX0DER",
    )
    for field, value in overrides.items():
        setattr(settings, field, value)
    return settings


class FakeAmazonClient:
    def __init__(
        self,
        *,
        catalog: dict[str, Any] | None = None,
        pricing: dict[str, dict[str, Any] | Exception] | None = None,
        fees: dict[str, dict[str, Any] | Exception] | None = None,
    ) -> None:
        self.catalog = catalog or {}
        self.pricing = pricing or {}
        self.fees = fees or {}
        self.calls: list[tuple[Any, ...]] = []

    def __enter__(self) -> FakeAmazonClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get_catalog_items(self, keywords: str, page_size: int = 10) -> dict[str, Any]:
        self.calls.append(("catalog", keywords, page_size))
        return self.catalog

    def get_competitive_pricing_for_asin(self, asin: str) -> dict[str, Any]:
        self.calls.append(("pricing", asin))
        response = self.pricing[asin]
        if isinstance(response, Exception):
            raise response
        return response

    def get_fees_estimate_for_asin(
        self,
        asin: str,
        listing_price: float,
    ) -> dict[str, Any]:
        self.calls.append(("fees", asin, listing_price))
        response = self.fees[asin]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.parametrize(
    "plugin_type",
    [AmazonCatalogSpApiPlugin, AmazonPricingSpApiPlugin, AmazonFeesSpApiPlugin],
)
def test_amazon_production_plugins_are_disabled_without_configuration(plugin_type: type) -> None:
    plugin = plugin_type(
        settings=_amazon_settings(amazon_sp_api_enabled=False),
        client_factory=lambda settings: pytest.fail("disabled plugin instantiated a client"),
    )

    assert plugin.enabled is False
    with pytest.raises(RuntimeError, match="disabled or incomplete"):
        plugin.fetch(IngestionQuery(query="ice roller", metadata={"asins": ["B000TEST01"]}))


def test_catalog_plugin_maps_amazon_items_to_raw_observations() -> None:
    fake = FakeAmazonClient(
        catalog={
            "items": [
                {
                    "asin": "B000TEST01",
                    "summaries": [
                        {
                            "itemName": "Reusable Facial Ice Roller",
                            "brand": "Glow Tools",
                            "browseClassification": {"displayName": "Beauty"},
                            "itemDimensions": {
                                "length": {"value": 7.5, "unit": "inches"},
                            },
                        }
                    ],
                    "productTypes": [{"productType": "BEAUTY"}],
                    "images": [{"images": [{"link": "https://example.com/ice-roller.jpg"}]}],
                    "salesRanks": [{"ranks": [{"rank": 1234}]}],
                }
            ]
        }
    )
    plugin = AmazonCatalogSpApiPlugin(
        settings=_amazon_settings(),
        client_factory=lambda settings: fake,
    )

    observations = plugin.fetch(IngestionQuery(query="facial ice roller", limit=10))

    assert fake.calls == [("catalog", "facial ice roller", 10)]
    assert len(observations) == 1
    observation = observations[0]
    assert isinstance(observation, RawObservationDTO)
    assert observation.entity_type == "marketplace_listing"
    assert observation.external_id == "B000TEST01"
    assert observation.metrics["sales_rank"] == 1234
    assert observation.metadata["brand"] == "Glow Tools"
    assert observation.metadata["product_type"] == "BEAUTY"
    assert observation.metadata["dimensions"]["length"]["value"] == 7.5
    assert observation.metadata["image_url"] == "https://example.com/ice-roller.jpg"


def test_pricing_plugin_maps_metrics_and_isolates_an_asin_failure() -> None:
    fake = FakeAmazonClient(
        pricing={
            "B000TEST01": {
                "payload": [
                    {
                        "ASIN": "B000TEST01",
                        "Product": {
                            "CompetitivePricing": {
                                "CompetitivePrices": [
                                    {
                                        "CompetitivePriceId": "1",
                                        "Price": {
                                            "LandedPrice": {
                                                "CurrencyCode": "USD",
                                                "Amount": 24.99,
                                            }
                                        },
                                    },
                                    {
                                        "CompetitivePriceId": "2",
                                        "Price": {
                                            "LandedPrice": {
                                                "CurrencyCode": "USD",
                                                "Amount": 23.49,
                                            }
                                        },
                                    },
                                ],
                                "NumberOfOfferListings": [{"Count": 7}],
                            },
                            "Offers": [
                                {"BuyingPrice": {"LandedPrice": {"Amount": 22.99}}}
                            ],
                        },
                    }
                ]
            },
            "B000FAIL02": RuntimeError("pricing unavailable"),
        }
    )
    plugin = AmazonPricingSpApiPlugin(
        settings=_amazon_settings(),
        client_factory=lambda settings: fake,
    )

    observations = plugin.fetch(
        IngestionQuery(metadata={"asins": ["B000TEST01", "B000FAIL02"]}, limit=10)
    )

    assert len(observations) == 1
    metrics = observations[0].metrics
    assert metrics == {
        "price": 24.99,
        "offer_count": 7,
        "seller_count": None,
        "featured_offer_price": 24.99,
        "competitive_price": 23.49,
        "lowest_offer_price": 22.99,
    }
    assert observations[0].metadata["request_errors"] == [
        {"asin": "B000FAIL02", "error": "pricing unavailable"}
    ]


def test_fees_plugin_maps_components_to_cost_model_evidence() -> None:
    fake = FakeAmazonClient(
        fees={
            "B000TEST01": {
                "payload": {
                    "FeesEstimateResult": {
                        "FeesEstimateIdentifier": {"Identifier": "B000TEST01:24.99"},
                        "FeesEstimate": {
                            "TotalFeesEstimate": {
                                "CurrencyCode": "USD",
                                "Amount": 8.75,
                            },
                            "FeeDetailList": [
                                {
                                    "FeeType": "ReferralFee",
                                    "FinalFee": {"CurrencyCode": "USD", "Amount": 3.75},
                                },
                                {
                                    "FeeType": "FBAFees",
                                    "FinalFee": {"CurrencyCode": "USD", "Amount": 5.00},
                                },
                            ],
                        },
                    }
                }
            }
        }
    )
    plugin = AmazonFeesSpApiPlugin(
        settings=_amazon_settings(),
        client_factory=lambda settings: fake,
    )

    observations = plugin.fetch(
        IngestionQuery(
            metadata={"asins": [{"asin": "B000TEST01", "modeled_price": 24.99}]}
        )
    )

    assert fake.calls == [("fees", "B000TEST01", 24.99)]
    assert len(observations) == 1
    observation = observations[0]
    assert observation.metrics["referral_fee_per_unit"] == 3.75
    assert observation.metrics["fulfillment_fee_per_unit"] == 5.0
    assert observation.metrics["total_amazon_fees"] == 8.75
    assert observation.metadata["model_name"] == "amazon_fba_fee_estimate"
    assert observation.metadata["fee_estimate_source"] == "amazon_spapi_product_fees"
    assert observation.metadata["comparable_asin"] == "B000TEST01"
    assert len(observation.metadata["fee_components"]) == 2


def test_comparable_analyzer_associates_asins_and_emits_modeled_outputs() -> None:
    context = ProductContext(
        product_id="product-1",
        canonical_name="facial ice roller",
        observations=[
            {
                "id": "catalog-observation",
                "source": "amazon_sp_api",
                "source_plugin": "amazon_catalog_spapi",
                "external_id": "B000TEST01",
                "metrics": {"sales_rank": 1234},
                "metadata": {"asin": "B000TEST01", "evidence_type": "amazon_catalog"},
            },
            {
                "id": "pricing-observation-1",
                "source": "amazon_sp_api",
                "source_plugin": "amazon_pricing_spapi",
                "external_id": "B000TEST01:pricing",
                "metrics": {"featured_offer_price": 24.99, "offer_count": 7},
                "metadata": {"asin": "B000TEST01", "evidence_type": "amazon_pricing"},
            },
            {
                "id": "pricing-observation-2",
                "source": "amazon_sp_api",
                "source_plugin": "amazon_pricing_spapi",
                "external_id": "B000TEST02:pricing",
                "metrics": {"competitive_price": 29.99, "offer_count": 4},
                "metadata": {"asin": "B000TEST02", "evidence_type": "amazon_pricing"},
            },
            {
                "id": "fees-observation",
                "source": "amazon_sp_api",
                "source_plugin": "amazon_fees_spapi",
                "external_id": "B000TEST01:fees:24.99",
                "metrics": {
                    "selling_price": 24.99,
                    "referral_fee_per_unit": 3.75,
                    "fulfillment_fee_per_unit": 5.0,
                    "total_amazon_fees": 8.75,
                },
                "metadata": {
                    "asin": "B000TEST01",
                    "evidence_type": "amazon_fees",
                    "currency": "USD",
                    "fee_components": [{"fee_type": "ReferralFee", "amount": 3.75}],
                },
            },
        ],
    )

    result = AmazonComparableAsinsAnalyzer().analyze(context)

    assert result.market_signals == []
    assert result.cost_models[0]["model_name"] == "amazon_fba_fee_estimate"
    assert result.cost_models[0]["marketplace_fee_per_unit"] == 3.75
    assert result.cost_models[0]["fulfillment_cost_per_unit"] == 5.0
    assert result.insights[0]["insight_type"] == "competition_summary"
    assert result.insights[0]["metadata"]["comparable_asins"] == [
        "B000TEST01",
        "B000TEST02",
    ]
    assert result.insights[0]["metadata"]["modeled_price"] == 29.99
    assert "modeled sale price is $29.99" in result.insights[0]["body"]
    assert "not guaranteed actual fees" in result.insights[0]["body"]


def test_listing_title_is_not_treated_as_customer_complaint() -> None:
    context = ProductContext(
        product_id="product-1",
        canonical_name="facial ice roller",
        observations=[
            {
                "id": "catalog-observation",
                "source": "amazon_sp_api",
                "source_plugin": "amazon_catalog_spapi",
                "entity_type": "marketplace_listing",
                "title": "Unbreakable steel cooling roller",
                "raw_text": None,
                "metrics": {},
                "metadata": {},
            }
        ],
    )

    review = ReviewAnalyzer().analyze(context)
    risk = RiskAnalyzer().analyze(context)

    assert review.insights[0]["metadata"]["complaint_count"] == 0
    assert len(review.insights) == 1
    assert risk.insights[0]["metadata"]["risk_score"] == 10
