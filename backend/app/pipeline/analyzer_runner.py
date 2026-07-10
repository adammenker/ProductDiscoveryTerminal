from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import (
    CostModel,
    InsightType,
    MarketSignal,
    MarketSignalType,
    PluginRun,
    PluginType,
    ProductInsight,
    RunStatus,
    SupplierSignal,
)
from app.plugins.registry import get_analyzer_plugins
from app.schemas.plugin import AnalyzerPlugin
from app.services.product_service import ProductService

logger = logging.getLogger(__name__)


class AnalyzerRunner:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.product_service = ProductService(db)

    def run(self, product_ids: list[uuid.UUID | str]) -> list[PluginRun]:
        self._replace_derived_snapshots(product_ids)
        runs: list[PluginRun] = []
        for plugin in get_analyzer_plugins():
            runs.append(self._run_plugin(plugin, product_ids))
        return runs

    def _replace_derived_snapshots(self, product_ids: list[uuid.UUID | str]) -> None:
        ids = [uuid.UUID(str(product_id)) for product_id in product_ids]
        if not ids:
            return
        for model in (MarketSignal, SupplierSignal, CostModel, ProductInsight):
            self.db.execute(delete(model).where(model.product_id.in_(ids)))
        self.db.commit()

    def _run_plugin(self, plugin: AnalyzerPlugin, product_ids: list[uuid.UUID | str]) -> PluginRun:
        run = PluginRun(
            plugin_name=plugin.name,
            plugin_type=PluginType.ANALYZER,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
            parameters={"product_count": len(product_ids)},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        records_created = 0
        errors: list[str] = []
        logger.info("Starting analyzer plugin %s for %s products", plugin.name, len(product_ids))
        for product_id in product_ids:
            try:
                context = self.product_service.build_context(product_id)
                result = plugin.analyze(context)
                records_created += self._persist_result(uuid.UUID(str(product_id)), result.model_dump())
                self.db.commit()
            except Exception as exc:  # noqa: BLE001
                self.db.rollback()
                errors.append(f"{product_id}: {exc}")
                logger.exception("Analyzer plugin %s failed for product %s", plugin.name, product_id)

        run.records_created = records_created
        run.finished_at = datetime.now(UTC)
        if errors and records_created:
            run.status = RunStatus.PARTIAL_SUCCESS
            run.error_message = "; ".join(errors)[:2000]
        elif errors:
            run.status = RunStatus.FAILED
            run.error_message = "; ".join(errors)[:2000]
        else:
            run.status = RunStatus.SUCCESS
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info("Finished analyzer plugin %s: %s records", plugin.name, records_created)
        return run

    def _persist_result(self, product_id: uuid.UUID, result: dict) -> int:
        created = 0
        for signal in result.get("market_signals", []):
            self.db.add(
                MarketSignal(
                    product_id=product_id,
                    source=signal.get("source") or "analyzer",
                    signal_type=MarketSignalType(signal["signal_type"]),
                    value=float(signal["value"]),
                    unit=signal.get("unit"),
                    window_start=signal.get("window_start"),
                    window_end=signal.get("window_end"),
                    metadata_=signal.get("metadata") or {},
                )
            )
            created += 1
        for signal in result.get("supplier_signals", []):
            self.db.add(
                SupplierSignal(
                    product_id=product_id,
                    source=signal.get("source") or "analyzer",
                    supplier_name=signal.get("supplier_name"),
                    supplier_url=signal.get("supplier_url"),
                    unit_cost=signal.get("unit_cost"),
                    moq=signal.get("moq"),
                    lead_time_days=signal.get("lead_time_days"),
                    shipping_estimate=signal.get("shipping_estimate"),
                    country=signal.get("country"),
                    metadata_=signal.get("metadata") or {},
                )
            )
            created += 1
        for cost_model in result.get("cost_models", []):
            self.db.add(
                CostModel(
                    product_id=product_id,
                    model_name=cost_model["model_name"],
                    selling_price=float(cost_model["selling_price"]),
                    unit_cost=cost_model.get("unit_cost"),
                    freight_cost_per_unit=cost_model.get("freight_cost_per_unit"),
                    packaging_cost_per_unit=cost_model.get("packaging_cost_per_unit"),
                    fulfillment_cost_per_unit=cost_model.get("fulfillment_cost_per_unit"),
                    marketplace_fee_per_unit=cost_model.get("marketplace_fee_per_unit"),
                    storage_cost_per_unit=cost_model.get("storage_cost_per_unit"),
                    estimated_gross_margin=cost_model.get("estimated_gross_margin"),
                    estimated_net_margin=cost_model.get("estimated_net_margin"),
                    currency=cost_model.get("currency") or "USD",
                    assumptions=cost_model.get("assumptions") or {},
                )
            )
            created += 1
        for insight in result.get("insights", []):
            self.db.add(
                ProductInsight(
                    product_id=product_id,
                    insight_type=InsightType(insight["insight_type"]),
                    title=insight["title"],
                    body=insight["body"],
                    confidence=float(insight.get("confidence") or 0.7),
                    evidence_observation_ids=insight.get("evidence_observation_ids") or [],
                    metadata_=insight.get("metadata") or {},
                )
            )
            created += 1
        return created
