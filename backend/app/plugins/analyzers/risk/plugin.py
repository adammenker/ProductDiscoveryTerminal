from __future__ import annotations

from app.schemas.plugin import AnalyzerResult, ProductContext


class RiskAnalyzer:
    name = "risk_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Creates operational and regulatory risk flags.",
        "supports": ["insights"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        text = " ".join(
            [
                context.canonical_name,
                *(observation.get("title") or "" for observation in context.observations),
                *(observation.get("raw_text") or "" for observation in context.observations),
            ]
        ).lower()

        risk_score = 10
        title = "Low operational risk"
        body = "No major regulatory, battery, liquid, fragile, or shipping complexity signals were detected."
        if any(term in text for term in ("supplement", "medical", "health claim", "medical-style")):
            risk_score = 85
            title = "Regulatory or claim risk"
            body = "Health or medical-claim language appears in the evidence, which raises regulatory and trust risk."
        elif any(term in text for term in ("battery", "charging", "liquid", "leak", "electronics")):
            risk_score = 60
            title = "Battery, liquid, or electronics risk"
            body = "Evidence mentions batteries, charging, leaks, or electronics, increasing fulfillment and returns risk."
        elif any(term in text for term in ("fragile", "warped", "bulky", "break")):
            risk_score = 35
            title = "Moderate handling risk"
            body = "Evidence suggests breakage, size, or handling concerns that may affect shipping and returns."

        return AnalyzerResult(
            insights=[
                {
                    "insight_type": "risk_flag",
                    "title": title,
                    "body": body,
                    "confidence": 0.7,
                    "evidence_observation_ids": [observation["id"] for observation in context.observations],
                    "metadata": {"risk_score": risk_score},
                }
            ]
        )

