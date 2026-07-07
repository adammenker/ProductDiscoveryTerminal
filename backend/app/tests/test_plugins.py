from __future__ import annotations

import pytest

from app.plugins.registry import get_analyzer_plugins, get_ingestion_plugins, list_plugins
from app.schemas.plugin import IngestionQuery, RawObservationDTO


def test_plugin_registry_lists_mvp_plugins() -> None:
    catalog = list_plugins()

    ingestion_names = {plugin.name for plugin in catalog["ingestion"]}
    analyzer_names = {plugin.name for plugin in catalog["analyzers"]}

    assert {
        "manual_csv",
        "amazon_mock",
        "alibaba_mock",
        "reddit_mock",
        "google_trends_mock",
        "etsy_api",
        "alibaba_open_api",
    }.issubset(ingestion_names)
    assert {
        "demand_analyzer",
        "competition_analyzer",
        "supplier_analyzer",
        "economics_analyzer",
        "risk_analyzer",
        "review_analyzer",
    }.issubset(analyzer_names)

    etsy_plugin = next(plugin for plugin in catalog["ingestion"] if plugin.name == "etsy_api")
    assert etsy_plugin.enabled is False
    alibaba_plugin = next(plugin for plugin in catalog["ingestion"] if plugin.name == "alibaba_open_api")
    assert alibaba_plugin.enabled is False


def test_ingestion_plugins_return_valid_dtos() -> None:
    for plugin in get_ingestion_plugins():
        observations = plugin.fetch(IngestionQuery(limit=2))
        assert observations
        assert all(isinstance(observation, RawObservationDTO) for observation in observations)
        assert all(observation.source_plugin == plugin.name for observation in observations)


def test_manual_csv_accepts_supplier_quote_fields() -> None:
    plugin = get_ingestion_plugins(["manual_csv"])[0]

    observation = plugin.fetch(IngestionQuery(limit=1))[0]

    assert observation.metrics["shipping_estimate"] == 1.35
    assert observation.metrics["lead_time_days"] == 24
    assert observation.metadata["supplier_name"] == "Ningbo Kitchenwares"
    assert observation.metadata["country"] == "CN"


def test_etsy_plugin_is_opt_in_until_configured() -> None:
    plugin = get_ingestion_plugins(["etsy_api"])[0]

    assert plugin.name == "etsy_api"
    with pytest.raises(RuntimeError, match="etsy_api is disabled"):
        plugin.fetch(IngestionQuery(query="ice roller", limit=1))


def test_alibaba_plugin_is_opt_in_until_configured() -> None:
    plugin = get_ingestion_plugins(["alibaba_open_api"])[0]

    assert plugin.name == "alibaba_open_api"
    with pytest.raises(RuntimeError, match="alibaba_open_api is disabled"):
        plugin.fetch(IngestionQuery(query="ice roller", limit=1))


def test_analyzer_plugins_have_manifests() -> None:
    for plugin in get_analyzer_plugins():
        assert plugin.name
        assert plugin.version
        assert plugin.manifest["type"] == "analyzer"
