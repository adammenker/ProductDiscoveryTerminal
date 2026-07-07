from __future__ import annotations

from typing import Any

PRODUCT_FIXTURES: list[dict[str, Any]] = [
    {
        "product_name": "facial ice roller",
        "category": "beauty",
        "price": 24.99,
        "review_count": 420,
        "rating": 4.2,
        "seller_count": 18,
        "bestseller_rank": 1850,
        "trend_score": 86,
        "growth_percent": 38,
        "unit_cost": 3.4,
        "moq": 300,
        "lead_time_days": 18,
        "shipping_estimate": 0.85,
        "supplier_name": "Shenzhen Glow Tools",
        "pain_text": (
            "People keep complaining that facial ice rollers do not stay cold long enough, "
            "handles loosen, and the roller head stops gliding after a few weeks."
        ),
        "risk_terms": ["simple", "non_electronic", "lightweight"],
    },
    {
        "product_name": "under sink drip tray",
        "category": "home",
        "price": 29.99,
        "review_count": 155,
        "rating": 4.1,
        "seller_count": 11,
        "bestseller_rank": 3200,
        "trend_score": 74,
        "growth_percent": 26,
        "unit_cost": 5.8,
        "moq": 250,
        "lead_time_days": 22,
        "shipping_estimate": 1.15,
        "supplier_name": "Ningbo Home Utility",
        "pain_text": (
            "Homeowners want an under sink drip tray that fits odd cabinets. Reviews mention "
            "thin plastic, warped edges, and trays that are hard to trim cleanly."
        ),
        "risk_terms": ["bulky"],
    },
    {
        "product_name": "pet hair remover roller",
        "category": "pets",
        "price": 19.99,
        "review_count": 980,
        "rating": 4.4,
        "seller_count": 34,
        "bestseller_rank": 980,
        "trend_score": 68,
        "growth_percent": 14,
        "unit_cost": 4.2,
        "moq": 500,
        "lead_time_days": 20,
        "shipping_estimate": 0.75,
        "supplier_name": "Yiwu Pet Supply",
        "pain_text": (
            "Buyers like reusable pet hair rollers but complain about flimsy hinges, small "
            "waste chambers, and poor performance on low-pile fabric."
        ),
        "risk_terms": ["simple"],
    },
    {
        "product_name": "portable blender",
        "category": "kitchen",
        "price": 39.99,
        "review_count": 3100,
        "rating": 4.0,
        "seller_count": 76,
        "bestseller_rank": 740,
        "trend_score": 62,
        "growth_percent": 6,
        "unit_cost": 10.75,
        "moq": 800,
        "lead_time_days": 35,
        "shipping_estimate": 3.25,
        "supplier_name": "Guangzhou Mini Appliance",
        "pain_text": (
            "Portable blender complaints focus on weak batteries, leaks near the blade base, "
            "charging failures, and difficult cleaning."
        ),
        "risk_terms": ["battery", "liquid", "electronics"],
    },
    {
        "product_name": "posture corrector brace",
        "category": "health",
        "price": 27.99,
        "review_count": 2400,
        "rating": 3.8,
        "seller_count": 49,
        "bestseller_rank": 1200,
        "trend_score": 58,
        "growth_percent": -3,
        "unit_cost": 4.9,
        "moq": 600,
        "lead_time_days": 24,
        "shipping_estimate": 0.95,
        "supplier_name": "Fujian Wellness Textile",
        "pain_text": (
            "Customers report posture corrector braces dig into armpits, roll up, have poor "
            "sizing, and make medical-style claims that create trust concerns."
        ),
        "risk_terms": ["medical_claims", "wearable"],
    },
]


def filter_fixtures(category: str | None, limit: int) -> list[dict[str, Any]]:
    rows = PRODUCT_FIXTURES
    if category:
        rows = [item for item in rows if str(item["category"]).lower() == category.lower()]
    return rows[:limit]
