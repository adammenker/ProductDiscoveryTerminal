from __future__ import annotations

from app.plugins.analyzers.competition.plugin import CompetitionAnalyzer
from app.plugins.analyzers.demand.plugin import DemandAnalyzer
from app.plugins.analyzers.economics.plugin import EconomicsAnalyzer
from app.plugins.analyzers.review.plugin import ReviewAnalyzer
from app.plugins.analyzers.risk.plugin import RiskAnalyzer
from app.plugins.analyzers.supplier.plugin import SupplierAnalyzer
from app.plugins.ingestion.alibaba_mock.plugin import AlibabaMockPlugin
from app.plugins.ingestion.amazon_mock.plugin import AmazonMockPlugin
from app.plugins.ingestion.etsy_api.plugin import EtsyApiPlugin
from app.plugins.ingestion.google_trends_mock.plugin import GoogleTrendsMockPlugin
from app.plugins.ingestion.manual_csv.plugin import ManualCsvPlugin
from app.plugins.ingestion.reddit_mock.plugin import RedditMockPlugin
from app.schemas.plugin import AnalyzerPlugin, IngestionPlugin, PluginInfo

INGESTION_PLUGINS: list[IngestionPlugin] = [
    ManualCsvPlugin(),
    AmazonMockPlugin(),
    AlibabaMockPlugin(),
    RedditMockPlugin(),
    GoogleTrendsMockPlugin(),
    EtsyApiPlugin(),
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
    return PluginInfo(
        name=plugin.name,
        version=plugin.version,
        enabled=_plugin_enabled(plugin),
        type=plugin_type,
        description=manifest.get("description"),
        supports=manifest.get("supports", []),
    )


def _plugin_enabled(plugin: IngestionPlugin | AnalyzerPlugin) -> bool:
    enabled = getattr(plugin, "enabled", True)
    return bool(enabled() if callable(enabled) else enabled)
