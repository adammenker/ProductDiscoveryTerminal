from __future__ import annotations

from typing import Any

from app.plugins.analyzers.competition.plugin import CompetitionAnalyzer
from app.plugins.analyzers.demand.plugin import DemandAnalyzer
from app.plugins.analyzers.economics.plugin import EconomicsAnalyzer
from app.plugins.analyzers.review.plugin import ReviewAnalyzer
from app.plugins.analyzers.risk.plugin import RiskAnalyzer
from app.plugins.analyzers.supplier.plugin import SupplierAnalyzer
from app.plugins.ingestion.alibaba_mock.plugin import AlibabaMockPlugin
from app.plugins.ingestion.alibaba_open_api.plugin import AlibabaOpenApiPlugin
from app.plugins.ingestion.amazon_mock.plugin import AmazonMockPlugin
from app.plugins.ingestion.amazon_sp_api.plugin import AmazonSpApiPlugin
from app.plugins.ingestion.etsy_api.plugin import EtsyApiPlugin
from app.plugins.ingestion.google_trends_mock.plugin import GoogleTrendsMockPlugin
from app.plugins.ingestion.manual_csv.plugin import ManualCsvPlugin
from app.plugins.ingestion.reddit_mock.plugin import RedditMockPlugin
from app.schemas.plugin import AnalyzerPlugin, IngestionPlugin, PluginInfo

INGESTION_PLUGINS: list[IngestionPlugin] = [
    ManualCsvPlugin(),
    AmazonMockPlugin(),
    AmazonSpApiPlugin(),
    AlibabaMockPlugin(),
    RedditMockPlugin(),
    GoogleTrendsMockPlugin(),
    EtsyApiPlugin(),
    AlibabaOpenApiPlugin(),
]

ANALYZER_PLUGINS: list[AnalyzerPlugin] = [
    DemandAnalyzer(),
    CompetitionAnalyzer(),
    SupplierAnalyzer(),
    EconomicsAnalyzer(),
    RiskAnalyzer(),
    ReviewAnalyzer(),
]


def get_ingestion_plugins(names: list[str] | None = None) -> list[IngestionPlugin]:
    if not names:
        return [plugin for plugin in INGESTION_PLUGINS if _plugin_enabled(plugin)]
    requested = set(names)
    return [plugin for plugin in INGESTION_PLUGINS if plugin.name in requested]


def get_analyzer_plugins() -> list[AnalyzerPlugin]:
    return ANALYZER_PLUGINS


def list_plugins() -> dict[str, list[PluginInfo]]:
    return {
        "ingestion": [_plugin_info(plugin, "ingestion") for plugin in INGESTION_PLUGINS],
        "analyzers": [_plugin_info(plugin, "analyzer") for plugin in ANALYZER_PLUGINS],
    }


def _plugin_info(plugin: IngestionPlugin | AnalyzerPlugin, plugin_type: str) -> PluginInfo:
    manifest = plugin.manifest
    configuration_status = _configuration_status(plugin)
    return PluginInfo(
        name=plugin.name,
        version=plugin.version,
        enabled=_plugin_enabled(plugin),
        type=plugin_type,
        description=manifest.get("description"),
        supports=manifest.get("supports", []),
        configured=configuration_status.get("configured"),
        environment=configuration_status.get("environment"),
        missing_credentials=configuration_status.get("missing_credentials", []),
    )


def _plugin_enabled(plugin: IngestionPlugin | AnalyzerPlugin) -> bool:
    enabled = getattr(plugin, "enabled", True)
    return bool(enabled() if callable(enabled) else enabled)


def _configuration_status(plugin: IngestionPlugin | AnalyzerPlugin) -> dict[str, Any]:
    status = getattr(plugin, "configuration_status", None)
    if callable(status):
        return dict(status())
    return {}
