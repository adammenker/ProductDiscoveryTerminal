from __future__ import annotations

import re

from app.schemas.plugin import AnalyzerResult, ProductContext

COMPLAINT_PATTERNS = (
    r"\bcomplain(?:s|ed|ing|t|ts)?\b",
    r"\bpoor\b",
    r"\bweak\b",
    r"\bhard\b",
    r"\bbreak(?:s|ing|age)?\b",
    r"\bleak(?:s|ed|ing|age)?\b",
    r"\bflimsy\b",
    r"\bdifficult\b",
    r"\bodou?r\b",
    r"\bzippers?\b",
    r"\bwarped\b",
    r"\broll up\b",
)
CUSTOMER_EVIDENCE_TYPES = {"review", "social_post", "forum_post"}


class ReviewAnalyzer:
    name = "review_analyzer"
    version = "0.1.0"
    manifest = {
        "name": name,
        "version": version,
        "type": "analyzer",
        "description": "Summarizes customer pain points and possible differentiation angles.",
        "supports": ["insights"],
    }

    def analyze(self, context: ProductContext) -> AnalyzerResult:
        complaint_observations = []
        snippets = []
        for observation in context.observations:
            source = str(observation.get("source") or "").lower()
            entity_type = str(observation.get("entity_type") or "").lower()
            if entity_type not in CUSTOMER_EVIDENCE_TYPES and not any(
                token in source for token in ("reddit", "review", "forum")
            ):
                continue
            text = f"{observation.get('title') or ''} {observation.get('raw_text') or ''}".lower()
            if any(re.search(pattern, text) for pattern in COMPLAINT_PATTERNS):
                complaint_observations.append(observation)
                snippets.append(observation.get("raw_text") or observation.get("title") or "")

        if not complaint_observations:
            return AnalyzerResult(
                insights=[
                    {
                        "insight_type": "review_summary",
                        "title": "Limited complaint evidence",
                        "body": "No repeated complaint cluster was detected in the available observations.",
                        "confidence": 0.45,
                        "evidence_observation_ids": [],
                        "metadata": {"complaint_count": 0},
                    }
                ]
            )

        evidence_ids = [observation["id"] for observation in complaint_observations]
        complaint_count = len(complaint_observations)
        body = " ".join(snippets[:3])
        return AnalyzerResult(
            insights=[
                {
                    "insight_type": "review_summary",
                    "title": "Customer pain summary",
                    "body": body,
                    "confidence": 0.72,
                    "evidence_observation_ids": evidence_ids,
                    "metadata": {"complaint_count": complaint_count},
                },
                {
                    "insight_type": "complaint_cluster",
                    "title": "Repeated quality or usability complaints",
                    "body": (
                        "Evidence contains repeated negative language around durability, fit, "
                        "ease of use, leakage, or weak materials."
                    ),
                    "confidence": 0.76,
                    "evidence_observation_ids": evidence_ids,
                    "metadata": {"complaint_count": complaint_count},
                },
                {
                    "insight_type": "feature_gap",
                    "title": "Durability and fit differentiation gap",
                    "body": (
                        "A version with sturdier materials, clearer sizing, better sealing, "
                        "or easier maintenance may justify a premium if economics hold."
                    ),
                    "confidence": 0.68,
                    "evidence_observation_ids": evidence_ids,
                    "metadata": {"complaint_count": complaint_count},
                },
                {
                    "insight_type": "differentiation_idea",
                    "title": "Premium execution angle",
                    "body": (
                        "Position the product around fewer failure points, better fit guidance, "
                        "and visible material quality instead of racing on price alone."
                    ),
                    "confidence": 0.64,
                    "evidence_observation_ids": evidence_ids,
                    "metadata": {"complaint_count": complaint_count},
                },
            ]
        )
