from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CandidateOrigin,
    OpportunityScore,
    ProductCandidate,
    RecommendationFeedback,
)

POSITIVE_LABELS = {
    "positive",
    "interesting",
    "actually_interesting",
    "good_recommendation",
    "pursue",
}
NEGATIVE_LABELS = {
    "negative",
    "unattractive",
    "actually_unattractive",
    "bad_recommendation",
    "skip",
}


@dataclass(frozen=True)
class ProductEvaluationRow:
    product_id: str
    canonical_name: str
    category: str | None
    scoring_version: str | None
    recommendation: str | None
    score: float | None
    label: str | None
    label_source: str | None
    feedback_reasons: list[str]
    discovery_sources: list[str]

    @property
    def binary_label(self) -> int | None:
        if self.label in POSITIVE_LABELS:
            return 1
        if self.label in NEGATIVE_LABELS:
            return 0
        return None


class EvaluationHarness:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(
        self,
        *,
        k: int = 10,
        golden_dataset_path: str | Path | None = None,
        scoring_versions: list[str] | None = None,
    ) -> dict[str, Any]:
        rows = self._rows(golden_dataset_path)
        if scoring_versions:
            allowed = set(scoring_versions)
            rows = [row for row in rows if row.scoring_version in allowed]
        ranked = sorted(
            [row for row in rows if row.score is not None],
            key=lambda row: row.score or -1,
            reverse=True,
        )
        labeled = [row for row in rows if row.binary_label is not None]
        return {
            "summary": {
                "products_evaluated": len(rows),
                "labeled_products": len(labeled),
                "scored_products": len(ranked),
                "k": k,
                "precision_at_k": precision_at_k(ranked, k),
                "ranking_agreement": ranking_agreement(labeled),
            },
            "false_positive_analysis": false_positive_analysis(ranked, k),
            "false_negative_analysis": false_negative_analysis(rows),
            "category_performance": grouped_performance(labeled, "category"),
            "discovery_source_performance": discovery_source_performance(labeled),
            "scoring_version_comparison": grouped_performance(labeled, "scoring_version"),
            "rows": [row.__dict__ for row in rows],
        }

    def write_reports(
        self,
        report: dict[str, Any],
        output_dir: str | Path,
        *,
        stem: str = "recommendation_v2_evaluation",
    ) -> dict[str, str]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        json_path = path / f"{stem}.json"
        markdown_path = path / f"{stem}.md"
        json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        markdown_path.write_text(markdown_report(report), encoding="utf-8")
        return {"json": str(json_path), "markdown": str(markdown_path)}

    def _rows(self, golden_dataset_path: str | Path | None) -> list[ProductEvaluationRow]:
        products = list(self.db.scalars(select(ProductCandidate)))
        latest_scores = self._latest_scores()
        feedback_labels = self._feedback_labels()
        golden_labels = load_golden_labels(golden_dataset_path)
        discovery_sources = self._discovery_sources()

        rows: list[ProductEvaluationRow] = []
        for product in products:
            score = latest_scores.get(str(product.id))
            golden = golden_labels.get(str(product.id)) or golden_labels.get(product.canonical_name.lower())
            feedback = feedback_labels.get(str(product.id))
            label = None
            label_source = None
            feedback_reasons: list[str] = []
            if golden:
                label = golden["label"]
                label_source = "golden_dataset"
            if feedback:
                label = feedback["label"]
                label_source = "analyst_feedback"
                feedback_reasons = feedback["reasons"]
            rows.append(
                ProductEvaluationRow(
                    product_id=str(product.id),
                    canonical_name=product.canonical_name,
                    category=product.category,
                    scoring_version=score.scoring_version if score else None,
                    recommendation=score.recommendation.value if score else None,
                    score=score.final_score if score else None,
                    label=label,
                    label_source=label_source,
                    feedback_reasons=feedback_reasons,
                    discovery_sources=discovery_sources.get(str(product.id), []),
                )
            )
        return rows

    def _latest_scores(self) -> dict[str, OpportunityScore]:
        rows = list(
            self.db.scalars(
                select(OpportunityScore).order_by(
                    OpportunityScore.product_id,
                    OpportunityScore.created_at.desc(),
                )
            )
        )
        latest: dict[str, OpportunityScore] = {}
        for row in rows:
            latest.setdefault(str(row.product_id), row)
        return latest

    def _feedback_labels(self) -> dict[str, dict[str, Any]]:
        rows = list(
            self.db.scalars(
                select(RecommendationFeedback).order_by(RecommendationFeedback.created_at.desc())
            )
        )
        labels: dict[str, dict[str, Any]] = {}
        for feedback in rows:
            product_id = str(feedback.product_id)
            if product_id in labels:
                continue
            label = _label_from_feedback(feedback.verdict, feedback.reasons)
            if label is None:
                continue
            labels[product_id] = {"label": label, "reasons": feedback.reasons}
        return labels

    def _discovery_sources(self) -> dict[str, list[str]]:
        sources: dict[str, set[str]] = {}
        for origin in self.db.scalars(select(CandidateOrigin)):
            sources.setdefault(str(origin.product_id), set()).add(origin.source_plugin)
        return {product_id: sorted(values) for product_id, values in sources.items()}


def load_golden_labels(path: str | Path | None) -> dict[str, dict[str, Any]]:
    dataset_path = Path(path) if path else Path(__file__).with_name("golden_dataset.json")
    if not dataset_path.exists():
        return {}
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    labels = payload.get("labels", payload if isinstance(payload, list) else [])
    result: dict[str, dict[str, Any]] = {}
    for item in labels:
        if not isinstance(item, dict) or not item.get("label"):
            continue
        key = item.get("product_id") or str(item.get("canonical_name", "")).lower()
        if key:
            result[str(key)] = item
    return result


def precision_at_k(ranked_rows: list[ProductEvaluationRow], k: int) -> float | None:
    top = ranked_rows[:k]
    labeled_top = [row for row in top if row.binary_label is not None]
    if not labeled_top:
        return None
    positives = sum(1 for row in labeled_top if row.binary_label == 1)
    return round(positives / len(labeled_top), 4)


def ranking_agreement(labeled_rows: list[ProductEvaluationRow]) -> float | None:
    scored = [row for row in labeled_rows if row.binary_label is not None and row.score is not None]
    comparisons = 0
    agreements = 0.0
    for left_index, left in enumerate(scored):
        for right in scored[left_index + 1 :]:
            if left.binary_label == right.binary_label:
                continue
            comparisons += 1
            positive = left if left.binary_label == 1 else right
            negative = right if left.binary_label == 1 else left
            if (positive.score or 0) > (negative.score or 0):
                agreements += 1
            elif positive.score == negative.score:
                agreements += 0.5
    if comparisons == 0:
        return None
    return round(agreements / comparisons, 4)


def false_positive_analysis(ranked_rows: list[ProductEvaluationRow], k: int) -> list[dict[str, Any]]:
    rows = [
        row
        for row in ranked_rows[:k]
        if row.binary_label == 0
        and row.recommendation in {"pursue", "investigate", "strong_opportunity"}
    ]
    return [
        {
            "product_id": row.product_id,
            "canonical_name": row.canonical_name,
            "score": row.score,
            "recommendation": row.recommendation,
            "reasons": row.feedback_reasons,
        }
        for row in rows
    ]


def false_negative_analysis(rows: list[ProductEvaluationRow]) -> list[dict[str, Any]]:
    misses = [
        row
        for row in rows
        if row.binary_label == 1
        and (row.score is None or row.recommendation in {"skip", "insufficient_data", "needs_more_data"})
    ]
    return [
        {
            "product_id": row.product_id,
            "canonical_name": row.canonical_name,
            "score": row.score,
            "recommendation": row.recommendation,
            "reasons": row.feedback_reasons,
        }
        for row in misses
    ]


def grouped_performance(rows: list[ProductEvaluationRow], attribute: str) -> list[dict[str, Any]]:
    groups: dict[str, list[ProductEvaluationRow]] = {}
    for row in rows:
        key = str(getattr(row, attribute) or "unknown")
        groups.setdefault(key, []).append(row)
    return [_performance_row(key, values) for key, values in sorted(groups.items())]


def discovery_source_performance(rows: list[ProductEvaluationRow]) -> list[dict[str, Any]]:
    groups: dict[str, list[ProductEvaluationRow]] = {}
    for row in rows:
        keys = row.discovery_sources or ["unknown"]
        for key in keys:
            groups.setdefault(key, []).append(row)
    return [_performance_row(key, values) for key, values in sorted(groups.items())]


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Recommendation V2 Evaluation",
        "",
        "## Summary",
        "",
        f"- Products evaluated: {summary['products_evaluated']}",
        f"- Labeled products: {summary['labeled_products']}",
        f"- Scored products: {summary['scored_products']}",
        f"- Precision@{summary['k']}: {_fmt(summary['precision_at_k'])}",
        f"- Ranking agreement: {_fmt(summary['ranking_agreement'])}",
        "",
        "## False Positives",
        "",
    ]
    lines.extend(_issue_lines(report["false_positive_analysis"]))
    lines.extend(["", "## False Negatives", ""])
    lines.extend(_issue_lines(report["false_negative_analysis"]))
    lines.extend(["", "## Category Performance", ""])
    lines.extend(_table_lines(report["category_performance"]))
    lines.extend(["", "## Discovery Source Performance", ""])
    lines.extend(_table_lines(report["discovery_source_performance"]))
    lines.extend(["", "## Scoring Version Comparison", ""])
    lines.extend(_table_lines(report["scoring_version_comparison"]))
    return "\n".join(lines) + "\n"


def console_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return (
        f"products={summary['products_evaluated']} "
        f"labeled={summary['labeled_products']} "
        f"precision@{summary['k']}={_fmt(summary['precision_at_k'])} "
        f"ranking_agreement={_fmt(summary['ranking_agreement'])}"
    )


def _label_from_feedback(verdict: str, reasons: list[str]) -> str | None:
    reason_set = set(reasons)
    if "actually_interesting" in reason_set or verdict == "good_recommendation":
        return "actually_interesting"
    if "actually_unattractive" in reason_set or verdict == "bad_recommendation":
        return "actually_unattractive"
    return None


def _performance_row(key: str, rows: list[ProductEvaluationRow]) -> dict[str, Any]:
    labeled = [row for row in rows if row.binary_label is not None]
    positives = sum(1 for row in labeled if row.binary_label == 1)
    avg_score_values = [row.score for row in rows if row.score is not None]
    return {
        "group": key,
        "products": len(rows),
        "labeled": len(labeled),
        "positives": positives,
        "precision": round(positives / len(labeled), 4) if labeled else None,
        "average_score": round(sum(avg_score_values) / len(avg_score_values), 2)
        if avg_score_values
        else None,
    }


def _issue_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- None"]
    return [
        f"- {row['canonical_name']} ({row['recommendation']}, score={_fmt(row['score'])})"
        for row in rows
    ]


def _table_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No labeled rows."]
    lines = ["| Group | Products | Labeled | Positives | Precision | Avg score |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(
            "| {group} | {products} | {labeled} | {positives} | {precision} | {average_score} |".format(
                group=row["group"],
                products=row["products"],
                labeled=row["labeled"],
                positives=row["positives"],
                precision=_fmt(row["precision"]),
                average_score=_fmt(row["average_score"]),
            )
        )
    return lines


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)
