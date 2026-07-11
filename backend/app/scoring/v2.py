from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from statistics import median
from typing import Any

from app.models.enums import InsightType, MarketSignalType
from app.scoring.config import (
    EVIDENCE_CONFIDENCE_WEIGHTS,
    READINESS_WEIGHTS,
    RECOMMENDATION_V2_THRESHOLDS,
    RECOMMENDATION_V2_WEIGHTS,
    SCORING_VERSION,
)
from app.scoring.formulas import clamp


def build_recommendation_v2(
    *,
    product_name: str,
    observations: list[dict[str, Any]],
    market_signals: list[dict[str, Any]],
    cost_models: list[dict[str, Any]],
    insights: list[dict[str, Any]],
    economics: dict[str, Any],
    supplier_validation: dict[str, Any],
    constraint_evaluation: dict[str, Any],
    evidence: dict[str, Any],
    comparable_rows: list[dict[str, Any]],
    derived_signals: dict[str, Any],
) -> dict[str, Any]:
    included_comparables = [
        row for row in comparable_rows if row.get("relevance_status") in {"included", "manually_included"}
    ]
    components = {
        "demand_proxy": demand_proxy_component(included_comparables, market_signals, derived_signals),
        "competition": competition_component(included_comparables, market_signals),
        "economics": economics_component(economics),
        "risk": risk_component(insights, constraint_evaluation),
    }
    data_quality = data_quality_component(
        observations=observations,
        components=components,
        comparable_rows=comparable_rows,
        included_comparables=included_comparables,
        evidence=evidence,
        economics=economics,
        derived_signals=derived_signals,
    )
    components["data_quality"] = data_quality

    opportunity_coverage = round(
        sum(component["coverage"] for component in components.values()) / len(components),
        1,
    )
    opportunity_score = weighted_score(components, opportunity_coverage)
    evidence_confidence_score = data_quality["value"] or 0
    validation_readiness_score = validation_readiness(
        included_comparables=included_comparables,
        economics=economics,
        supplier_validation=supplier_validation,
        constraint_evaluation=constraint_evaluation,
        insights=insights,
        derived_signals=derived_signals,
    )

    missing_evidence = _missing_evidence(
        components=components,
        evidence=evidence,
        included_comparables=included_comparables,
        economics=economics,
        derived_signals=derived_signals,
    )
    blocking_issues = _blocking_issues(
        components=components,
        economics=economics,
        constraint_evaluation=constraint_evaluation,
        comparable_rows=comparable_rows,
    )
    recommendation, reasons = recommendation_rule(
        opportunity_score=opportunity_score,
        opportunity_coverage=opportunity_coverage,
        evidence_confidence_score=evidence_confidence_score,
        validation_readiness_score=validation_readiness_score,
        economics=economics,
        supplier_validation=supplier_validation,
        constraint_evaluation=constraint_evaluation,
        included_comparables=included_comparables,
        missing_evidence=missing_evidence,
        blocking_issues=blocking_issues,
    )
    next_actions = _next_actions(recommendation, missing_evidence, blocking_issues)
    explanation = _explanation(
        product_name=product_name,
        recommendation=recommendation,
        opportunity_score=opportunity_score,
        evidence_confidence_score=evidence_confidence_score,
        validation_readiness_score=validation_readiness_score,
        reasons=reasons,
        missing_evidence=missing_evidence,
    )

    return {
        "opportunity_score": opportunity_score,
        "opportunity_coverage": opportunity_coverage,
        "evidence_confidence_score": evidence_confidence_score,
        "validation_readiness_score": validation_readiness_score,
        "recommendation": recommendation,
        "recommendation_reasons": reasons,
        "missing_evidence": missing_evidence,
        "blocking_issues": blocking_issues,
        "next_actions": next_actions,
        "components": components,
        "scoring_version": SCORING_VERSION,
        "explanation": explanation,
        "weights": RECOMMENDATION_V2_WEIGHTS,
        "thresholds": RECOMMENDATION_V2_THRESHOLDS,
        "comparable_summary": {
            "total": len(comparable_rows),
            "included": len(included_comparables),
            "needs_review": len(
                [row for row in comparable_rows if row.get("relevance_status") == "needs_review"]
            ),
            "average_included_relevance": _mean(
                row.get("relevance_score") for row in included_comparables
            ),
        },
    }


def component(
    *,
    name: str,
    value: float | None,
    status: str,
    coverage: float,
    confidence: float,
    evidence_count: int,
    freshness_days: int | None,
    evidence_ids: list[str],
    explanation: str,
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": round(value, 1) if value is not None else None,
        "status": status,
        "coverage": round(clamp(coverage), 1),
        "confidence": round(clamp(confidence), 1),
        "evidence_count": evidence_count,
        "freshness_days": freshness_days,
        "evidence_ids": evidence_ids,
        "explanation": explanation,
        "warnings": warnings or [],
        "metadata": metadata or {},
    }


def demand_proxy_component(
    comparables: list[dict[str, Any]],
    market_signals: list[dict[str, Any]],
    derived_signals: dict[str, Any],
) -> dict[str, Any]:
    bsr_values = [
        float(row["metadata"]["bestseller_rank"])
        for row in comparables
        if (row.get("metadata") or {}).get("bestseller_rank") is not None
    ]
    direct_volume = _signal_values(market_signals, MarketSignalType.SEARCH_VOLUME.value)
    direct_growth = _signal_values(market_signals, MarketSignalType.SEARCH_GROWTH.value)
    trend_values = _signal_values(market_signals, MarketSignalType.TREND_SCORE.value)
    evidence_ids = _signal_ids(market_signals, {
        MarketSignalType.SEARCH_VOLUME.value,
        MarketSignalType.SEARCH_GROWTH.value,
        MarketSignalType.TREND_SCORE.value,
        MarketSignalType.BESTSELLER_RANK.value,
    })

    if not bsr_values and not direct_volume and not direct_growth and not trend_values:
        return component(
            name="demand_proxy",
            value=None,
            status="missing",
            coverage=0,
            confidence=0,
            evidence_count=0,
            freshness_days=None,
            evidence_ids=[],
            explanation="No BSR, Product Opportunity Explorer, trend, or historical demand proxy evidence is available.",
            warnings=["Demand proxy cannot be estimated reliably."],
            metadata={"direct_demand_data_available": False},
        )

    scores: list[float] = []
    metadata: dict[str, Any] = {"direct_demand_data_available": bool(direct_volume or direct_growth)}
    warnings = ["Demand is inferred from marketplace proxies."]
    if bsr_values:
        median_bsr = median(bsr_values)
        metadata.update(
            {
                "median_bsr": median_bsr,
                "p25_bsr": _percentile(bsr_values, 25),
                "p75_bsr": _percentile(bsr_values, 75),
                "included_comparables": len(comparables),
                "bsr_coverage_percent": round(100 * len(bsr_values) / max(1, len(comparables)), 1),
                "bsr_dispersion": round(max(bsr_values) / max(1, min(bsr_values)), 2),
            }
        )
        scores.append(_bsr_score(median_bsr))
    if direct_volume:
        scores.append(min(100, median(direct_volume) / 20))
    if direct_growth:
        scores.append(40 + clamp(median(direct_growth), -30, 60))
    elif trend_values:
        scores.append(clamp(median(trend_values)))

    history = (derived_signals.get("windows") or {}).get("30d") or {}
    bsr_delta = history.get("bsr_delta")
    if bsr_delta is not None:
        scores.append(70 if bsr_delta < 0 else 40)
        metadata["historical_bsr_delta_30d"] = bsr_delta

    coverage = 35
    coverage += 25 if bsr_values else 0
    coverage += 25 if direct_volume or direct_growth else 0
    coverage += 15 if bsr_delta is not None else 0
    confidence = coverage * 0.75 + min(20, len(bsr_values) * 2)
    return component(
        name="demand_proxy",
        value=_mean(scores),
        status="measured" if direct_volume or direct_growth else "inferred",
        coverage=coverage,
        confidence=confidence,
        evidence_count=len(bsr_values) + len(direct_volume) + len(direct_growth) + len(trend_values),
        freshness_days=None,
        evidence_ids=evidence_ids,
        explanation=(
            "Demand is estimated from median comparable BSR and available direct/trend proxies. "
            "Static review count is not treated as demand."
        ),
        warnings=warnings,
        metadata=metadata,
    )


def competition_component(
    comparables: list[dict[str, Any]],
    market_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    prices = [float(row["price"]) for row in comparables if row.get("price") is not None]
    seller_counts = [
        float(row["metadata"]["seller_count"])
        for row in comparables
        if (row.get("metadata") or {}).get("seller_count") is not None
    ] or _signal_values(market_signals, MarketSignalType.SELLER_COUNT.value)
    review_counts = [
        float(row["metadata"]["review_count"])
        for row in comparables
        if (row.get("metadata") or {}).get("review_count") is not None
    ] or _signal_values(market_signals, MarketSignalType.REVIEW_COUNT.value)
    brands = [
        str(row.get("brand")).strip().lower()
        for row in comparables
        if row.get("brand")
    ]

    if not prices and not seller_counts and not review_counts and not brands:
        return component(
            name="competition",
            value=None,
            status="missing",
            coverage=0,
            confidence=0,
            evidence_count=0,
            freshness_days=None,
            evidence_ids=[],
            explanation="No relevant review-moat, offer-count, brand, or price evidence is available.",
            warnings=["Competition cannot be estimated reliably."],
            metadata={},
        )

    score = 75.0
    metadata: dict[str, Any] = {
        "included_comparables": len(comparables),
        "unique_brands": len(set(brands)),
    }
    warnings: list[str] = []
    if seller_counts:
        median_sellers = median(seller_counts)
        metadata["median_seller_count"] = median_sellers
        score -= min(25, median_sellers * 0.7)
    if review_counts:
        median_reviews = median(review_counts)
        p75_reviews = _percentile(review_counts, 75)
        metadata.update(
            {
                "median_review_count": median_reviews,
                "p75_review_count": p75_reviews,
                "review_moat_500_percent": round(100 * len([x for x in review_counts if x >= 500]) / len(review_counts), 1),
                "review_moat_1000_percent": round(100 * len([x for x in review_counts if x >= 1000]) / len(review_counts), 1),
            }
        )
        if median_reviews >= 1000 or p75_reviews >= 5000:
            warnings.append("High review moat.")
            score -= 25
        elif median_reviews >= 500:
            score -= 15
    else:
        warnings.append("Review moat evidence is missing; confidence is lower.")

    if brands:
        brand_counts = Counter(brands)
        top_share = max(brand_counts.values()) / len(brands)
        metadata["top_brand_share_percent"] = round(top_share * 100, 1)
        if top_share >= 0.55:
            score -= 15
            warnings.append("Dominant brand concentration.")
        elif len(brand_counts) >= max(3, len(brands) // 2):
            score += 8
            metadata["brand_market"] = "fragmented_brand_market"
    else:
        warnings.append("Brand concentration is unknown.")

    if len(prices) >= 3:
        median_price = median(prices)
        within_5 = len([price for price in prices if median_price and abs(price - median_price) / median_price <= 0.05])
        compression = round(100 * within_5 / len(prices), 1)
        metadata.update(
            {
                "median_price": median_price,
                "price_iqr": round(_percentile(prices, 75) - _percentile(prices, 25), 2),
                "price_compression_percent": compression,
            }
        )
        if compression >= 60:
            score -= 18
            warnings.append("Price competition is high.")

    coverage = 20
    coverage += 20 if prices else 0
    coverage += 20 if seller_counts else 0
    coverage += 25 if review_counts else 0
    coverage += 15 if brands else 0
    confidence = coverage - (10 if not review_counts else 0)
    return component(
        name="competition",
        value=score,
        status="measured",
        coverage=coverage,
        confidence=confidence,
        evidence_count=len(prices) + len(seller_counts) + len(review_counts) + len(brands),
        freshness_days=None,
        evidence_ids=[],
        explanation="Competition attractiveness is scored so higher is better: fragmented, less review-heavy, less compressed markets score higher.",
        warnings=warnings,
        metadata=metadata,
    )


def economics_component(economics: dict[str, Any]) -> dict[str, Any]:
    modeled = economics.get("modeled") or {}
    modeled_price = economics.get("modeled_price")
    amazon_fees = economics.get("amazon_fees")
    if modeled_price is None:
        return component(
            name="economics",
            value=None,
            status="missing_price",
            coverage=0,
            confidence=0,
            evidence_count=0,
            freshness_days=None,
            evidence_ids=[],
            explanation="No modeled Amazon selling price is available.",
            warnings=["Economics cannot be modeled without price evidence."],
            metadata={},
        )
    if amazon_fees is None:
        return component(
            name="economics",
            value=None,
            status="missing_fees",
            coverage=35,
            confidence=20,
            evidence_count=1,
            freshness_days=None,
            evidence_ids=[],
            explanation="Price evidence exists, but Amazon fee evidence is missing.",
            warnings=["Fee evidence is required before economics can be scored."],
            metadata={"modeled_price": modeled_price},
        )

    max_landed_cost = modeled.get("max_landed_cost")
    fee_source = economics.get("fee_source")
    value: float | None
    if max_landed_cost is None:
        value = None
        status = "missing"
    elif max_landed_cost <= 0:
        value = 10.0
        status = "negative"
    else:
        value = clamp(45 + (float(max_landed_cost) / max(1.0, float(modeled_price))) * 200)
        status = "positive_unvalidated"
    if fee_source != "amazon_spapi_product_fees":
        status = "proxy_only"
    return component(
        name="economics",
        value=value,
        status=status,
        coverage=90 if fee_source == "amazon_spapi_product_fees" else 65,
        confidence=85 if fee_source == "amazon_spapi_product_fees" else 45,
        evidence_count=2,
        freshness_days=None,
        evidence_ids=[],
        explanation="Amazon pricing and fees are converted into a max landed cost; supplier cost is not required for discovery-stage opportunity score.",
        warnings=["Supplier quote still required for business validation."] if status == "positive_unvalidated" else [],
        metadata={
            "modeled_price": modeled_price,
            "amazon_fees": amazon_fees,
            "max_landed_cost": max_landed_cost,
            "fee_source": fee_source,
            "comparable_asin": economics.get("comparable_asin"),
        },
    )


def risk_component(
    insights: list[dict[str, Any]],
    constraint_evaluation: dict[str, Any],
) -> dict[str, Any]:
    risk_insights = [
        insight for insight in insights if insight.get("insight_type") == InsightType.RISK_FLAG.value
    ]
    hard_failures = constraint_evaluation.get("hard_failures") or []
    risk_flags = constraint_evaluation.get("risk_flags") or []
    severe = [
        flag for flag in risk_flags if flag.get("severity") in {"high", "severe"}
    ]
    if hard_failures:
        value: float | None = 0.0
        status = "measured"
        warnings = ["Hard constraint failure blocks pursue."]
    elif severe:
        value = 20.0
        status = "measured"
        warnings = ["Severe risk flags require review."]
    elif risk_insights or risk_flags:
        values = []
        for insight in risk_insights:
            raw_score = (insight.get("metadata") or {}).get("risk_score")
            if raw_score is not None:
                values.append(float(raw_score))
        value = 100.0 - max(values) if values else 70.0
        status = "measured"
        warnings = []
    else:
        value = None
        status = "missing"
        warnings = ["Risk evidence has not been measured."]
    return component(
        name="risk",
        value=value,
        status=status,
        coverage=80 if status == "measured" else 10,
        confidence=80 if status == "measured" else 10,
        evidence_count=len(risk_insights) + len(risk_flags),
        freshness_days=None,
        evidence_ids=[
            evidence_id
            for insight in risk_insights
            for evidence_id in insight.get("evidence_observation_ids") or []
        ],
        explanation="Risk score is oriented so higher is safer. Hard constraints and severe risk flags lower the score.",
        warnings=warnings,
        metadata={"risk_flags": risk_flags, "hard_failures": hard_failures},
    )


def data_quality_component(
    *,
    observations: list[dict[str, Any]],
    components: dict[str, dict[str, Any]],
    comparable_rows: list[dict[str, Any]],
    included_comparables: list[dict[str, Any]],
    evidence: dict[str, Any],
    economics: dict[str, Any],
    derived_signals: dict[str, Any],
) -> dict[str, Any]:
    coverage_score = _mean(component["coverage"] for component in components.values()) or 0
    comparable_relevance = _mean(row.get("relevance_score") for row in included_comparables) or 0
    freshness = freshness_score(observations)
    history = historical_depth_score(derived_signals)
    sources = {observation.get("source") for observation in observations if observation.get("source")}
    independence = min(100, len(sources) * 25)
    consistency = internal_consistency_score(economics, comparable_rows)
    value = (
        EVIDENCE_CONFIDENCE_WEIGHTS["evidence_coverage"] * coverage_score
        + EVIDENCE_CONFIDENCE_WEIGHTS["comparable_relevance"] * comparable_relevance
        + EVIDENCE_CONFIDENCE_WEIGHTS["freshness"] * freshness
        + EVIDENCE_CONFIDENCE_WEIGHTS["historical_depth"] * history
        + EVIDENCE_CONFIDENCE_WEIGHTS["source_independence"] * independence
        + EVIDENCE_CONFIDENCE_WEIGHTS["internal_consistency"] * consistency
    )
    missing = evidence.get("missing_evidence") or []
    warnings = list(missing[:4])
    return component(
        name="data_quality",
        value=value,
        status="measured" if observations else "missing",
        coverage=coverage_score,
        confidence=value,
        evidence_count=len(observations),
        freshness_days=_freshness_days(observations),
        evidence_ids=[str(observation.get("id")) for observation in observations if observation.get("id")],
        explanation="Evidence confidence measures coverage, comparable relevance, freshness, historical depth, source independence, and consistency.",
        warnings=warnings,
        metadata={
            "coverage_score": round(coverage_score, 1),
            "comparable_relevance": round(comparable_relevance, 1),
            "freshness": round(freshness, 1),
            "historical_depth": round(history, 1),
            "source_independence": round(independence, 1),
            "internal_consistency": round(consistency, 1),
        },
    )


def weighted_score(
    components: dict[str, dict[str, Any]],
    opportunity_coverage: float,
) -> float | None:
    if opportunity_coverage < RECOMMENDATION_V2_THRESHOLDS["minimum_opportunity_coverage"]:
        return None
    measured = {
        name: component
        for name, component in components.items()
        if component["value"] is not None and component["status"] not in {"missing", "not_applicable"}
    }
    if not measured:
        return None
    weight_sum = sum(RECOMMENDATION_V2_WEIGHTS[name] for name in measured)
    return round(
        sum(
            (RECOMMENDATION_V2_WEIGHTS[name] / weight_sum) * component["value"]
            for name, component in measured.items()
        ),
        2,
    )


def validation_readiness(
    *,
    included_comparables: list[dict[str, Any]],
    economics: dict[str, Any],
    supplier_validation: dict[str, Any],
    constraint_evaluation: dict[str, Any],
    insights: list[dict[str, Any]],
    derived_signals: dict[str, Any],
) -> float:
    risk_evaluated = any(insight.get("insight_type") == InsightType.RISK_FLAG.value for insight in insights)
    direct_demand = False
    history_measured = any(
        (row or {}).get("status") == "measured"
        for row in (derived_signals.get("windows") or {}).values()
    )
    checklist = {
        "relevant_comparables": 100 if included_comparables else 0,
        "price_data": 100 if economics.get("modeled_price") is not None else 0,
        "fee_data": 100 if economics.get("fee_source") == "amazon_spapi_product_fees" else 0,
        "constraints_evaluated": 100 if constraint_evaluation.get("rule_profile_id") else 0,
        "risk_evaluated": 100 if risk_evaluated or constraint_evaluation.get("risk_flags") is not None else 0,
        "historical_data": 100 if history_measured else 0,
        "direct_demand_data": 100 if direct_demand else 0,
        "supplier_validation": 100 if supplier_validation.get("viable_quote_count") else 0,
    }
    return round(sum(READINESS_WEIGHTS[key] * value for key, value in checklist.items()), 1)


def recommendation_rule(
    *,
    opportunity_score: float | None,
    opportunity_coverage: float,
    evidence_confidence_score: float,
    validation_readiness_score: float,
    economics: dict[str, Any],
    supplier_validation: dict[str, Any],
    constraint_evaluation: dict[str, Any],
    included_comparables: list[dict[str, Any]],
    missing_evidence: list[str],
    blocking_issues: list[str],
) -> tuple[str, list[str]]:
    if not constraint_evaluation.get("eligible", True):
        return "skip", ["Hard constraints failed."]
    if economics.get("decision") in {"quote_above_ceiling", "invalid_negative_ceiling"}:
        return "skip", ["Modeled economics are structurally weak."]
    if blocking_issues:
        return "skip", blocking_issues[:3]
    if (
        opportunity_score is None
        or opportunity_coverage < RECOMMENDATION_V2_THRESHOLDS["minimum_opportunity_coverage"]
        or evidence_confidence_score < RECOMMENDATION_V2_THRESHOLDS["minimum_investigate_confidence"]
        or not included_comparables
        or economics.get("modeled_price") is None
        or economics.get("fee_source") != "amazon_spapi_product_fees"
    ):
        return "insufficient_data", ["Minimum evidence coverage has not been met."]
    if (
        supplier_validation.get("viable_quote_count")
        and opportunity_score >= RECOMMENDATION_V2_THRESHOLDS["investigate_score"]
        and evidence_confidence_score >= RECOMMENDATION_V2_THRESHOLDS["minimum_pursue_confidence"]
        and validation_readiness_score >= RECOMMENDATION_V2_THRESHOLDS["minimum_pursue_readiness"]
    ):
        return "pursue", ["Fully validated product clears discovery, confidence, readiness, and supplier gates."]
    if opportunity_score >= RECOMMENDATION_V2_THRESHOLDS["investigate_score"]:
        return "investigate", ["Attractive discovery-stage opportunity; validation work remains."]
    if opportunity_score >= RECOMMENDATION_V2_THRESHOLDS["watch_score"]:
        return "watch", ["Evidence is mixed or not historically established."]
    return "skip", ["Opportunity score is too weak."]


def freshness_score(observations: list[dict[str, Any]]) -> float:
    days = _freshness_days(observations)
    if days is None:
        return 0
    if days <= 7:
        return 100
    if days <= 30:
        return 80
    if days <= 90:
        return 50
    return 20


def historical_depth_score(derived_signals: dict[str, Any]) -> float:
    windows = derived_signals.get("windows") or {}
    measured = [row for row in windows.values() if (row or {}).get("status") == "measured"]
    if len(measured) >= 3:
        return 100
    if len(measured) == 2:
        return 70
    if len(measured) == 1:
        return 40
    return 0


def internal_consistency_score(
    economics: dict[str, Any],
    comparable_rows: list[dict[str, Any]],
) -> float:
    prices = [float(row["price"]) for row in comparable_rows if row.get("price") is not None]
    score = 100.0
    if len(prices) >= 2 and min(prices) > 0 and max(prices) / min(prices) >= 1.5:
        score -= 35
    if economics.get("fee_source") != "amazon_spapi_product_fees":
        score -= 25
    if any(row.get("relevance_status") == "needs_review" for row in comparable_rows):
        score -= 15
    return clamp(score)


def _missing_evidence(
    *,
    components: dict[str, dict[str, Any]],
    evidence: dict[str, Any],
    included_comparables: list[dict[str, Any]],
    economics: dict[str, Any],
    derived_signals: dict[str, Any],
) -> list[str]:
    missing = set(evidence.get("missing_evidence") or [])
    for name, item in components.items():
        if item["value"] is None or item["status"] == "missing":
            missing.add(f"Missing {name.replace('_', ' ')} evidence")
    if not included_comparables:
        missing.add("Need relevant comparable ASINs")
    if economics.get("fee_source") != "amazon_spapi_product_fees":
        missing.add("Need live Amazon fee estimate")
    if not any((row or {}).get("status") == "measured" for row in (derived_signals.get("windows") or {}).values()):
        missing.add("Need historical marketplace snapshots")
    return sorted(missing)


def _blocking_issues(
    *,
    components: dict[str, dict[str, Any]],
    economics: dict[str, Any],
    constraint_evaluation: dict[str, Any],
    comparable_rows: list[dict[str, Any]],
) -> list[str]:
    issues: list[str] = []
    if not constraint_evaluation.get("eligible", True):
        issues.append("Hard constraints failed.")
    if economics.get("decision") in {"quote_above_ceiling", "invalid_negative_ceiling"}:
        issues.append("Modeled max landed cost is not viable.")
    if components["risk"]["value"] is not None and components["risk"]["value"] < 25:
        issues.append("Severe risk flags detected.")
    if comparable_rows and not any(row.get("relevance_status") in {"included", "manually_included"} for row in comparable_rows):
        issues.append("No comparable ASIN passed relevance filtering.")
    return issues


def _next_actions(
    recommendation: str,
    missing_evidence: list[str],
    blocking_issues: list[str],
) -> list[str]:
    if blocking_issues:
        return ["Review blocking issues before additional sourcing work.", *blocking_issues[:2]]
    actions = []
    if "Need relevant comparable ASINs" in missing_evidence:
        actions.append("Review comparable ASINs and include/exclude the right product type.")
    if "Need live Amazon fee estimate" in missing_evidence:
        actions.append("Refresh Amazon fee estimates for included comparables.")
    if "Need historical marketplace snapshots" in missing_evidence:
        actions.append("Refresh the product over time to build price, BSR, and seller-count history.")
    if "Need supplier quote" in missing_evidence:
        actions.append("Get a manual supplier quote once marketplace evidence is strong enough.")
    if not actions and recommendation == "investigate":
        actions.append("Validate supplier landed cost against the max landed cost ceiling.")
    return actions[:5]


def _explanation(
    *,
    product_name: str,
    recommendation: str,
    opportunity_score: float | None,
    evidence_confidence_score: float,
    validation_readiness_score: float,
    reasons: list[str],
    missing_evidence: list[str],
) -> str:
    score_text = "not generated" if opportunity_score is None else f"{opportunity_score:.1f}"
    reason_text = reasons[0] if reasons else "Recommendation uses measured evidence only."
    missing_text = (
        f" Missing evidence: {', '.join(missing_evidence[:3])}."
        if missing_evidence
        else ""
    )
    return (
        f"{product_name} is {recommendation} under recommendation_v2. "
        f"Opportunity {score_text}, confidence {evidence_confidence_score:.1f}, "
        f"readiness {validation_readiness_score:.1f}. {reason_text}{missing_text}"
    )


def _signal_values(market_signals: list[dict[str, Any]], signal_type: str) -> list[float]:
    return [
        float(signal["value"])
        for signal in market_signals
        if signal.get("signal_type") == signal_type and signal.get("value") is not None
    ]


def _signal_ids(market_signals: list[dict[str, Any]], signal_types: set[str]) -> list[str]:
    ids: list[str] = []
    for signal in market_signals:
        if signal.get("signal_type") not in signal_types:
            continue
        observation_id = (signal.get("metadata") or {}).get("observation_id")
        if observation_id:
            ids.append(str(observation_id))
    return ids


def _bsr_score(rank: float) -> float:
    if rank <= 100:
        return 90
    if rank <= 1_000:
        return 80
    if rank <= 10_000:
        return 65
    if rank <= 50_000:
        return 45
    return 25


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0
    values = sorted(values)
    index = (len(values) - 1) * percentile / 100
    lower = int(index)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return round(values[lower], 2)
    fraction = index - lower
    return round(values[lower] * (1 - fraction) + values[upper] * fraction, 2)


def _mean(values: Any) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    return round(sum(numbers) / len(numbers), 1) if numbers else None


def _freshness_days(observations: list[dict[str, Any]]) -> int | None:
    observed_at = [
        value
        for observation in observations
        if (value := observation.get("observed_at")) is not None
    ]
    if not observed_at:
        return None
    latest = max(observed_at)
    if isinstance(latest, str):
        latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    return max(0, (datetime.now(UTC) - latest).days)
