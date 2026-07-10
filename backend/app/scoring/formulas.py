from __future__ import annotations

from statistics import mean

from app.models.enums import InsightType, MarketSignalType, Recommendation
from app.scoring.config import SCORING_WEIGHTS


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def recommendation_for_score(final_score: float, confidence_score: float) -> Recommendation:
    if confidence_score < 50:
        return Recommendation.NEEDS_MORE_DATA
    if final_score >= 85:
        return Recommendation.STRONG_OPPORTUNITY
    if final_score >= 70:
        return Recommendation.INVESTIGATE
    if final_score >= 50:
        return Recommendation.WATCH
    if final_score >= 30:
        return Recommendation.NEEDS_MORE_DATA
    return Recommendation.SKIP


def weighted_final_score(components: dict[str, float]) -> float:
    final_score = (
        SCORING_WEIGHTS["demand"] * components["demand_score"]
        + SCORING_WEIGHTS["growth"] * components["growth_score"]
        + SCORING_WEIGHTS["margin"] * components["margin_score"]
        + SCORING_WEIGHTS["pain_point"] * components["pain_point_score"]
        + SCORING_WEIGHTS["competition"] * components["competition_score"]
        + SCORING_WEIGHTS["risk"] * components["risk_score"]
    )
    return round(clamp(final_score), 2)


def demand_score(observations: list[dict], market_signals: list[dict]) -> float:
    sources = {observation["source"] for observation in observations}
    trend_values = _signal_values(market_signals, MarketSignalType.TREND_SCORE.value)
    volume_values = _signal_values(market_signals, MarketSignalType.SEARCH_VOLUME.value)
    review_values = _signal_values(market_signals, MarketSignalType.REVIEW_COUNT.value)
    social_values = _signal_values(market_signals, MarketSignalType.SOCIAL_MENTIONS.value)
    rank_values = _signal_values(market_signals, MarketSignalType.BESTSELLER_RANK.value)

    signal_score = float(min(10, len(sources) * 5))
    if trend_values:
        signal_score += min(20, mean(trend_values) / 5)
    if volume_values:
        signal_score += min(15, mean(volume_values) / 80)
    if review_values:
        signal_score += min(15, mean(review_values) / 80)
    if social_values:
        signal_score += min(10, mean(social_values) / 3)
    if rank_values:
        best_rank = min(rank_values)
        signal_score += (
            30
            if best_rank <= 100
            else 25
            if best_rank <= 1_000
            else 18
            if best_rank <= 10_000
            else 10
            if best_rank <= 50_000
            else 5
        )

    return round(clamp(signal_score), 2)


def growth_score(market_signals: list[dict]) -> float:
    growth_values = _signal_values(market_signals, MarketSignalType.SEARCH_GROWTH.value)
    trend_values = _signal_values(market_signals, MarketSignalType.TREND_SCORE.value)
    if growth_values:
        growth = mean(growth_values)
        if growth < 0:
            return 20
        if growth < 10:
            return 50
        if growth < 30:
            return 70
        return 90
    if trend_values:
        return round(clamp(mean(trend_values)), 2)
    return 0


def competition_score(market_signals: list[dict]) -> float:
    review_values = _signal_values(market_signals, MarketSignalType.REVIEW_COUNT.value)
    seller_values = _signal_values(market_signals, MarketSignalType.SELLER_COUNT.value)
    rating_values = _signal_values(market_signals, MarketSignalType.RATING.value)

    reviews = mean(review_values) if review_values else 0
    sellers = mean(seller_values) if seller_values else 0
    rating = mean(rating_values) if rating_values else 0

    if reviews > 2500 or sellers > 60:
        base = 25
    elif reviews > 1000 or sellers > 35:
        base = 40
    elif reviews > 300 or sellers > 15:
        base = 65
    else:
        base = 82

    if rating and rating < 4.1:
        base += 8
    elif rating and rating > 4.5:
        base -= 8
    return round(clamp(base), 2)


def margin_score(cost_models: list[dict]) -> float:
    margins = [
        float(cost_model["estimated_net_margin"])
        for cost_model in cost_models
        if cost_model.get("estimated_net_margin") is not None
    ]
    if not margins:
        return 30
    margin = mean(margins)
    if margin < 20:
        return 20
    if margin < 35:
        return 50
    if margin < 50:
        return 70
    return 90


def pain_point_score(insights: list[dict]) -> float:
    complaint_insights = [
        insight
        for insight in insights
        if insight.get("insight_type")
        in {
            InsightType.COMPLAINT_CLUSTER.value,
            InsightType.FEATURE_GAP.value,
            InsightType.REVIEW_SUMMARY.value,
            InsightType.DIFFERENTIATION_IDEA.value,
        }
    ]
    if not complaint_insights:
        return 40
    complaint_count = max(
        int((insight.get("metadata") or {}).get("complaint_count") or 0)
        for insight in complaint_insights
    )
    if complaint_count == 0:
        return 40
    has_feature_gap = any(
        insight.get("insight_type") in {InsightType.FEATURE_GAP.value, InsightType.DIFFERENTIATION_IDEA.value}
        for insight in complaint_insights
    )
    if complaint_count >= 2 and has_feature_gap:
        return 90
    if complaint_count >= 1 and has_feature_gap:
        return 75
    return 55


def risk_score(insights: list[dict]) -> float:
    risk_values = []
    for insight in insights:
        if insight.get("insight_type") != InsightType.RISK_FLAG.value:
            continue
        value = (insight.get("metadata") or {}).get("risk_score")
        if value is not None:
            risk_values.append(float(value))
    if not risk_values:
        return 10
    return round(clamp(max(risk_values)), 2)


def confidence_score(
    observations: list[dict],
    market_signals: list[dict],
    supplier_signals: list[dict],
    cost_models: list[dict],
    insights: list[dict],
) -> float:
    confidence = 0
    sources = {observation["source"] for observation in observations}
    if observations:
        confidence += 20
    if market_signals:
        confidence += 20
    if supplier_signals:
        confidence += 20
    if cost_models:
        confidence += 20
    if any(
        insight.get("insight_type")
        in {InsightType.REVIEW_SUMMARY.value, InsightType.COMPLAINT_CLUSTER.value, InsightType.FEATURE_GAP.value}
        and bool(insight.get("evidence_observation_ids"))
        and int((insight.get("metadata") or {}).get("complaint_count") or 0) > 0
        for insight in insights
    ):
        confidence += 10
    if len(sources) >= 3:
        confidence += 10
    return clamp(confidence)


def _signal_values(market_signals: list[dict], signal_type: str) -> list[float]:
    return [
        float(signal["value"])
        for signal in market_signals
        if signal.get("signal_type") == signal_type and signal.get("value") is not None
    ]
