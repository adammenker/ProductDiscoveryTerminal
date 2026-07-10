from __future__ import annotations

import re

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
        if _contains(text, r"\b(?:supplement|medical|health claim|medical-style)\b"):
            risk_score = 85
            title = "Regulatory or claim risk"
            body = "Health or medical-claim language appears in the evidence, which raises regulatory and trust risk."
        elif _contains(text, r"\b(?:battery|charging|liquid|leaks?|electronics)\b"):
            risk_score = 60
            title = "Battery, liquid, or electronics risk"
            body = "Evidence mentions batteries, charging, leaks, or electronics, increasing fulfillment and returns risk."
        elif _contains(text, r"\b(?:fragile|warped|bulky|breaks?|breakage)\b"):
            risk_score = 35
            title = "Moderate handling risk"
            body = "Evidence suggests breakage, size, or handling concerns that may affect shipping and returns."

        structured_flags = []
        flag_terms = {
            "battery": ("battery", "charging", "rechargeable"),
            "liquid": ("liquid", "leak", "serum", "oil"),
            "supplement": ("supplement", "vitamin", "gummy", "capsule"),
            "medical_claim": ("medical", "cure", "treatment"),
            "fragile": ("fragile", "glass", "break", "breakage"),
            "electronics": ("electronics", "electronic", "usb"),
            "children_product": ("child", "kid", "baby"),
            "skin_contact": ("skin", "facial", "face"),
            "seasonal": ("christmas", "halloween", "seasonal"),
        }
        for risk_type, terms in flag_terms.items():
            evidence = [term for term in terms if _contains(text, rf"\b{re.escape(term)}\b")]
            if evidence:
                structured_flags.append(
                    {
                        "risk_type": risk_type,
                        "severity": "high"
                        if risk_type in {"battery", "liquid", "supplement", "fragile"}
                        else "medium",
                        "confidence": 0.75,
                        "evidence": evidence,
                        "source": "risk_analyzer",
                    }
                )

        return AnalyzerResult(
            insights=[
                {
                    "insight_type": "risk_flag",
                    "title": title,
                    "body": body,
                    "confidence": 0.7,
                    "evidence_observation_ids": [observation["id"] for observation in context.observations],
                    "metadata": {"risk_score": risk_score, "risk_flags": structured_flags},
                }
            ]
        )


def _contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text) is not None
