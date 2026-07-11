from __future__ import annotations

import math
import re
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComparableAsin, MarketplaceAsinSnapshot, ProductCandidate, RawObservation

AMAZON_COMPARABLE_PLUGINS = {
    "amazon_catalog_spapi",
    "amazon_pricing_spapi",
    "amazon_fees_spapi",
}
INCLUDED_RELEVANCE_STATUSES = {"included", "manually_included"}
COMPARABLE_RELEVANCE_VERSION = "comparable_relevance_v1"
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "in",
    "of",
    "on",
    "pack",
    "pcs",
    "set",
    "the",
    "to",
    "with",
}


class ComparableService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def sync_product(
        self,
        product_id: uuid.UUID | str,
        *,
        create_snapshots: bool = True,
    ) -> list[ComparableAsin]:
        product = self._product(product_id)
        observations = list(
            self.db.scalars(
                select(RawObservation)
                .where(RawObservation.product_id == product.id)
                .order_by(RawObservation.observed_at.asc(), RawObservation.created_at.asc())
            )
        )
        aggregate = self._aggregate_observations(observations)
        if not aggregate:
            return self.list_comparables(product.id, sync=False)

        existing = {
            row.asin: row
            for row in self.db.scalars(
                select(ComparableAsin).where(ComparableAsin.product_id == product.id)
            )
        }
        price_median = _safe_median(
            row["price"]
            for row in aggregate.values()
            if row.get("price") is not None and float(row["price"]) > 0
        )

        rows: list[ComparableAsin] = []
        for asin, row in aggregate.items():
            comparable = existing.get(asin)
            relevance = self._relevance(product, row, price_median)
            now = datetime.now(UTC)
            if comparable is None:
                comparable = ComparableAsin(
                    product_id=product.id,
                    asin=asin,
                    relevance_score=relevance["score"],
                    relevance_status=relevance["status"],
                    relevance_reasons=relevance["reasons"],
                    automatic_relevance_version=COMPARABLE_RELEVANCE_VERSION,
                    manually_overridden=False,
                    discovered_at=row.get("first_observed_at") or now,
                    last_refreshed_at=row.get("last_observed_at") or now,
                    metadata_={},
                )
                self.db.add(comparable)

            self._apply_observation_fields(comparable, row)
            comparable.last_refreshed_at = row.get("last_observed_at") or now
            comparable.metadata_ = {
                **(comparable.metadata_ or {}),
                "automatic_relevance": relevance,
                "latest_source_observation_ids": row.get("source_observation_ids") or [],
                "price_median_at_relevance": price_median,
                "bestseller_rank": row.get("bestseller_rank"),
                "featured_offer_price": row.get("featured_offer_price"),
                "lowest_offer_price": row.get("lowest_offer_price"),
                "offer_count": row.get("offer_count"),
                "seller_count": row.get("seller_count"),
                "review_count": row.get("review_count"),
                "rating": row.get("rating"),
                "fee_estimate": row.get("fee_estimate"),
                "fulfillment_fee": row.get("fulfillment_fee"),
                "referral_fee": row.get("referral_fee"),
            }
            if not comparable.manually_overridden:
                comparable.relevance_score = relevance["score"]
                comparable.relevance_status = relevance["status"]
                comparable.relevance_reasons = relevance["reasons"]
                comparable.automatic_relevance_version = COMPARABLE_RELEVANCE_VERSION

            rows.append(comparable)

        self.db.commit()
        for comparable_row in rows:
            self.db.refresh(comparable_row)
            if create_snapshots and comparable_row.relevance_status in INCLUDED_RELEVANCE_STATUSES:
                aggregate_row = aggregate[comparable_row.asin]
                if _has_snapshot_value(aggregate_row):
                    self.db.add(
                        _snapshot_from_row(
                            product.id,
                            comparable_row.id,
                            comparable_row.asin,
                            aggregate_row,
                        )
                    )
        self.db.commit()
        return self.list_comparables(product.id, sync=False)

    def list_comparables(
        self,
        product_id: uuid.UUID | str,
        *,
        sync: bool = True,
    ) -> list[ComparableAsin]:
        if sync:
            return self.sync_product(product_id, create_snapshots=False)
        return list(
            self.db.scalars(
                select(ComparableAsin)
                .where(ComparableAsin.product_id == uuid.UUID(str(product_id)))
                .order_by(
                    ComparableAsin.manually_overridden.desc(),
                    ComparableAsin.relevance_score.desc(),
                    ComparableAsin.asin.asc(),
                )
            )
        )

    def included_asins(self, product_id: uuid.UUID | str) -> set[str]:
        rows = self.list_comparables(product_id, sync=False)
        return {
            row.asin.upper()
            for row in rows
            if row.relevance_status in INCLUDED_RELEVANCE_STATUSES
        }

    def has_comparable_set(self, product_id: uuid.UUID | str) -> bool:
        return bool(self.list_comparables(product_id, sync=False))

    def update_relevance(
        self,
        product_id: uuid.UUID | str,
        asin: str,
        *,
        relevance_status: str,
        reason: str | None = None,
    ) -> ComparableAsin:
        product = self._product(product_id)
        comparable = self.db.scalar(
            select(ComparableAsin).where(
                ComparableAsin.product_id == product.id,
                ComparableAsin.asin == asin.upper(),
            )
        )
        if comparable is None:
            raise HTTPException(status_code=404, detail="Comparable ASIN not found")

        if relevance_status == "reset_automatic_decision":
            relevance = (comparable.metadata_ or {}).get("automatic_relevance") or {}
            comparable.manually_overridden = False
            comparable.manual_override_reason = None
            comparable.relevance_score = float(relevance.get("score") or comparable.relevance_score)
            comparable.relevance_status = str(relevance.get("status") or "needs_review")
            comparable.relevance_reasons = list(relevance.get("reasons") or comparable.relevance_reasons)
        else:
            allowed = {
                "included",
                "needs_review",
                "excluded_irrelevant",
                "excluded_wrong_product_type",
                "excluded_price_outlier",
                "excluded_brand_specific",
                "manually_included",
                "manually_excluded",
            }
            if relevance_status not in allowed:
                raise HTTPException(status_code=422, detail="Unsupported relevance status")
            if relevance_status == "included":
                relevance_status = "manually_included"
            elif relevance_status.startswith("excluded_"):
                relevance_status = "manually_excluded"
            comparable.manually_overridden = True
            comparable.relevance_status = relevance_status
            comparable.manual_override_reason = reason
            if reason:
                comparable.relevance_reasons = [reason, *comparable.relevance_reasons[:4]]
        self.db.commit()
        self.db.refresh(comparable)
        return comparable

    def history(self, product_id: uuid.UUID | str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.db.scalars(
            select(MarketplaceAsinSnapshot)
            .where(MarketplaceAsinSnapshot.product_id == uuid.UUID(str(product_id)))
            .order_by(MarketplaceAsinSnapshot.observed_at.desc(), MarketplaceAsinSnapshot.id.desc())
            .limit(limit)
        )
        return [_snapshot_dict(row) for row in rows]

    def derived_signals(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        snapshots = list(
            self.db.scalars(
                select(MarketplaceAsinSnapshot)
                .where(MarketplaceAsinSnapshot.product_id == uuid.UUID(str(product_id)))
                .order_by(MarketplaceAsinSnapshot.observed_at.asc(), MarketplaceAsinSnapshot.id.asc())
            )
        )
        windows = [7, 30, 90]
        return {
            "windows": {
                f"{days}d": _window_signal(snapshots, days)
                for days in windows
            },
            "snapshot_count": len(snapshots),
            "asin_count": len({row.asin for row in snapshots}),
            "latest_observation_at": snapshots[-1].observed_at if snapshots else None,
        }

    def comparable_summary(self, product_id: uuid.UUID | str) -> dict[str, Any]:
        rows = self.list_comparables(product_id, sync=False)
        included = [row for row in rows if row.relevance_status in INCLUDED_RELEVANCE_STATUSES]
        needs_review = [row for row in rows if row.relevance_status == "needs_review"]
        excluded = [row for row in rows if row.relevance_status.startswith("excluded") or row.relevance_status == "manually_excluded"]
        return {
            "total": len(rows),
            "included": len(included),
            "needs_review": len(needs_review),
            "excluded": len(excluded),
            "average_relevance_score": round(
                sum(row.relevance_score for row in included) / len(included),
                1,
            )
            if included
            else None,
            "included_asins": [row.asin for row in included],
        }

    def to_dict(self, comparable: ComparableAsin, selected_asin: str | None = None) -> dict[str, Any]:
        return {
            "id": str(comparable.id),
            "product_id": str(comparable.product_id),
            "asin": comparable.asin,
            "title": comparable.title,
            "brand": comparable.brand,
            "product_type": comparable.product_type,
            "category": comparable.category,
            "price": comparable.price,
            "currency": comparable.currency,
            "dimensions": comparable.dimensions,
            "weight": comparable.weight,
            "relevance_score": comparable.relevance_score,
            "relevance_status": comparable.relevance_status,
            "relevance_reasons": comparable.relevance_reasons,
            "automatic_relevance_version": comparable.automatic_relevance_version,
            "manually_overridden": comparable.manually_overridden,
            "manual_override_reason": comparable.manual_override_reason,
            "discovered_from_query": comparable.discovered_from_query,
            "discovered_at": comparable.discovered_at,
            "last_refreshed_at": comparable.last_refreshed_at,
            "metadata": comparable.metadata_,
            "selected_proxy": comparable.asin == selected_asin,
            "url": f"https://www.amazon.com/dp/{comparable.asin}",
            "source": "amazon_sp_api",
        }

    def _product(self, product_id: uuid.UUID | str) -> ProductCandidate:
        product = self.db.get(ProductCandidate, uuid.UUID(str(product_id)))
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    def _aggregate_observations(
        self,
        observations: list[RawObservation],
    ) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for observation in observations:
            metadata = observation.metadata_ or {}
            evidence_type = metadata.get("evidence_type")
            if (
                observation.source_plugin not in AMAZON_COMPARABLE_PLUGINS
                and evidence_type not in {"amazon_catalog", "amazon_pricing", "amazon_fees"}
            ):
                continue
            asin = metadata.get("asin") or metadata.get("comparable_asin")
            if not asin and observation.external_id:
                asin = observation.external_id.split(":", 1)[0]
            asin = str(asin or "").upper().split(":", 1)[0]
            if len(asin) != 10:
                continue
            row = rows.setdefault(
                asin,
                {
                    "asin": asin,
                    "source_observation_ids": [],
                    "first_observed_at": observation.observed_at,
                    "last_observed_at": observation.observed_at,
                },
            )
            row["source_observation_ids"].append(str(observation.id))
            if observation.observed_at < row["first_observed_at"]:
                row["first_observed_at"] = observation.observed_at
            if observation.observed_at > row["last_observed_at"]:
                row["last_observed_at"] = observation.observed_at

            metrics = observation.metrics or {}
            if evidence_type == "amazon_catalog" or observation.source_plugin == "amazon_catalog_spapi":
                row["title"] = metadata.get("title") or observation.title or row.get("title")
                row["brand"] = metadata.get("brand") or row.get("brand")
                row["product_type"] = metadata.get("product_type") or row.get("product_type")
                row["category"] = metadata.get("category") or row.get("category")
                row["dimensions"] = metadata.get("dimensions") or row.get("dimensions")
                row["discovered_from_query"] = metadata.get("product_name") or row.get("discovered_from_query")
                row["bestseller_rank"] = (
                    metrics.get("bestseller_rank")
                    or metrics.get("sales_rank")
                    or metadata.get("sales_rank")
                    or row.get("bestseller_rank")
                )
            if evidence_type == "amazon_pricing" or observation.source_plugin == "amazon_pricing_spapi":
                row["price"] = _first_number(
                    metrics.get("featured_offer_price"),
                    metrics.get("competitive_price"),
                    metrics.get("lowest_offer_price"),
                    metrics.get("price"),
                    row.get("price"),
                )
                row["featured_offer_price"] = _first_number(metrics.get("featured_offer_price"), row.get("featured_offer_price"))
                row["lowest_offer_price"] = _first_number(metrics.get("lowest_offer_price"), row.get("lowest_offer_price"))
                row["offer_count"] = _first_number(metrics.get("offer_count"), row.get("offer_count"))
                row["seller_count"] = _first_number(metrics.get("seller_count"), row.get("seller_count"))
                row["currency"] = metadata.get("currency") or row.get("currency") or "USD"
            if evidence_type == "amazon_fees" or observation.source_plugin == "amazon_fees_spapi":
                row["fee_estimate"] = _first_number(metrics.get("total_amazon_fees"), row.get("fee_estimate"))
                row["fulfillment_fee"] = _first_number(metrics.get("fulfillment_fee_per_unit"), row.get("fulfillment_fee"))
                row["referral_fee"] = _first_number(metrics.get("referral_fee_per_unit"), row.get("referral_fee"))
                row["currency"] = metadata.get("currency") or row.get("currency") or "USD"
            row["review_count"] = _first_number(metrics.get("review_count"), row.get("review_count"))
            row["rating"] = _first_number(metrics.get("rating"), row.get("rating"))
        return rows

    def _apply_observation_fields(self, comparable: ComparableAsin, row: dict[str, Any]) -> None:
        comparable.title = row.get("title") or comparable.title
        comparable.brand = row.get("brand") or comparable.brand
        comparable.product_type = row.get("product_type") or comparable.product_type
        comparable.category = row.get("category") or comparable.category
        comparable.price = row.get("price") if row.get("price") is not None else comparable.price
        comparable.currency = row.get("currency") or comparable.currency or "USD"
        comparable.dimensions = row.get("dimensions") or comparable.dimensions
        comparable.discovered_from_query = row.get("discovered_from_query") or comparable.discovered_from_query

    def _relevance(
        self,
        product: ProductCandidate,
        row: dict[str, Any],
        price_median: float | None,
    ) -> dict[str, Any]:
        title = str(row.get("title") or "")
        target_tokens = _tokens(" ".join([product.canonical_name, product.category or ""]))
        title_tokens = _tokens(title)
        overlap = len(target_tokens & title_tokens)
        required_overlap = len(target_tokens - STOPWORDS)
        overlap_ratio = overlap / max(1, required_overlap)
        score = 20 + min(45, overlap_ratio * 45)
        reasons: list[str] = []
        warnings: list[str] = []

        if overlap:
            reasons.append(f"{overlap} product-token overlap")
        else:
            warnings.append("No meaningful title overlap with candidate concept.")

        category = str(row.get("category") or "").lower()
        product_type = str(row.get("product_type") or "").lower()
        category_tokens = _tokens(category)
        product_type_tokens = _tokens(product_type)
        if category and target_tokens & category_tokens:
            score += 12
            reasons.append("Amazon category is compatible.")
        if product_type and target_tokens & product_type_tokens:
            score += 12
            reasons.append("Amazon product type overlaps target concept.")
        elif product_type and overlap_ratio < 0.45:
            score -= 15
            warnings.append(f"Product type may be different: {row.get('product_type')}.")

        price = row.get("price")
        if price is not None and price_median and price_median > 0:
            price = float(price)
            if price < price_median * 0.35 or price > price_median * 3.0:
                score -= 25
                warnings.append("Price is an outlier relative to the comparable set.")
            else:
                score += 8
                reasons.append("Price is plausible within the comparable set.")

        if _brand_specific_title(product.canonical_name, title):
            score -= 10
            warnings.append("Title appears brand-specific relative to a generic product concept.")

        score = round(max(0.0, min(100.0, score)), 1)
        if any("Price is an outlier" in warning for warning in warnings):
            status = "excluded_price_outlier"
        elif score >= 75:
            status = "included"
        elif score >= 50:
            status = "needs_review"
        elif product_type and overlap_ratio < 0.45:
            status = "excluded_wrong_product_type"
        else:
            status = "excluded_irrelevant"

        return {
            "score": score,
            "status": status,
            "reasons": [*reasons, *warnings],
            "overlap_ratio": round(overlap_ratio, 3),
            "target_tokens": sorted(target_tokens),
            "title_tokens": sorted(title_tokens),
        }


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def _first_number(*values: Any) -> float | None:
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return round(number, 2)
    return None


def _safe_median(values: Any) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(median(numbers), 2) if numbers else None


def _has_snapshot_value(row: dict[str, Any]) -> bool:
    return any(
        row.get(key) is not None
        for key in (
            "price",
            "featured_offer_price",
            "lowest_offer_price",
            "seller_count",
            "offer_count",
            "bestseller_rank",
            "review_count",
            "rating",
            "fee_estimate",
        )
    )


def _snapshot_from_row(
    product_id: uuid.UUID,
    comparable_asin_id: uuid.UUID,
    asin: str,
    row: dict[str, Any],
) -> MarketplaceAsinSnapshot:
    return MarketplaceAsinSnapshot(
        product_id=product_id,
        comparable_asin_id=comparable_asin_id,
        asin=asin,
        observed_at=row.get("last_observed_at") or datetime.now(UTC),
        price=row.get("price"),
        featured_offer_price=row.get("featured_offer_price"),
        lowest_offer_price=row.get("lowest_offer_price"),
        offer_count=row.get("offer_count"),
        seller_count=row.get("seller_count"),
        bestseller_rank=row.get("bestseller_rank"),
        bestseller_category=row.get("category"),
        review_count=row.get("review_count"),
        rating=row.get("rating"),
        fee_estimate=row.get("fee_estimate"),
        fulfillment_fee=row.get("fulfillment_fee"),
        referral_fee=row.get("referral_fee"),
        source_observation_ids=row.get("source_observation_ids") or [],
        metadata_={
            "snapshot_source": "comparable_service",
            "automatic_relevance_version": COMPARABLE_RELEVANCE_VERSION,
        },
    )


def _snapshot_dict(snapshot: MarketplaceAsinSnapshot) -> dict[str, Any]:
    return {
        "id": str(snapshot.id),
        "product_id": str(snapshot.product_id),
        "comparable_asin_id": str(snapshot.comparable_asin_id) if snapshot.comparable_asin_id else None,
        "asin": snapshot.asin,
        "observed_at": snapshot.observed_at,
        "price": snapshot.price,
        "featured_offer_price": snapshot.featured_offer_price,
        "lowest_offer_price": snapshot.lowest_offer_price,
        "offer_count": snapshot.offer_count,
        "seller_count": snapshot.seller_count,
        "bestseller_rank": snapshot.bestseller_rank,
        "bestseller_category": snapshot.bestseller_category,
        "review_count": snapshot.review_count,
        "rating": snapshot.rating,
        "fee_estimate": snapshot.fee_estimate,
        "fulfillment_fee": snapshot.fulfillment_fee,
        "referral_fee": snapshot.referral_fee,
        "source_observation_ids": snapshot.source_observation_ids,
        "metadata": snapshot.metadata_,
        "created_at": snapshot.created_at,
    }


def _window_signal(snapshots: list[MarketplaceAsinSnapshot], days: int) -> dict[str, Any]:
    if not snapshots:
        return {
            "window_days": days,
            "sample_count": 0,
            "coverage": 0,
            "status": "missing",
            "latest_observation_at": None,
        }
    latest_at = snapshots[-1].observed_at
    cutoff = latest_at - timedelta(days=days)
    window_rows = [row for row in snapshots if row.observed_at >= cutoff]
    asins = {row.asin for row in window_rows}
    span_days = (
        (window_rows[-1].observed_at - window_rows[0].observed_at).days
        if len(window_rows) >= 2
        else 0
    )
    status = "measured" if len(window_rows) >= 2 and span_days >= max(1, int(days * 0.5)) else "insufficient_history"
    return {
        "window_days": days,
        "sample_count": len(window_rows),
        "coverage": min(100, len(asins) * 20),
        "latest_observation_at": latest_at,
        "status": status,
        "price_delta": _delta(window_rows, "price") if status == "measured" else None,
        "seller_count_delta": _delta(window_rows, "seller_count") if status == "measured" else None,
        "offer_count_delta": _delta(window_rows, "offer_count") if status == "measured" else None,
        "bsr_delta": _delta(window_rows, "bestseller_rank") if status == "measured" else None,
        "review_count_delta": _delta(window_rows, "review_count") if status == "measured" else None,
        "comparable_set_churn": _churn(window_rows) if status == "measured" else None,
    }


def _delta(rows: list[MarketplaceAsinSnapshot], field: str) -> float | None:
    first_values = [getattr(row, field) for row in rows[: max(1, len(rows) // 3)] if getattr(row, field) is not None]
    last_values = [getattr(row, field) for row in rows[-max(1, len(rows) // 3) :] if getattr(row, field) is not None]
    if not first_values or not last_values:
        return None
    return round(float(median(last_values)) - float(median(first_values)), 2)


def _churn(rows: list[MarketplaceAsinSnapshot]) -> float | None:
    if len(rows) < 2:
        return None
    first = {row.asin for row in rows[: max(1, len(rows) // 3)]}
    last = {row.asin for row in rows[-max(1, len(rows) // 3) :]}
    union = first | last
    return round(100 * (1 - len(first & last) / len(union)), 1) if union else None


def _brand_specific_title(product_name: str, title: str) -> bool:
    product_tokens = _tokens(product_name)
    title_tokens = [token for token in re.findall(r"[A-Za-z0-9]+", title) if len(token) > 2]
    proper_tokens = {token.lower() for token in title_tokens if token[:1].isupper()}
    return bool(proper_tokens - product_tokens) and len(product_tokens & set(map(str.lower, title_tokens))) <= 1


def status_counts(rows: list[ComparableAsin]) -> dict[str, int]:
    counts = Counter(row.relevance_status for row in rows)
    return dict(sorted(counts.items()))
