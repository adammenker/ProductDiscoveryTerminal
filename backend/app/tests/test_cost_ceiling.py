from __future__ import annotations

from app.economics.cost_ceiling import CostCeilingInputs, calculate_cost_ceiling


def test_cost_ceiling_formula_and_quote_decision() -> None:
    result = calculate_cost_ceiling(
        CostCeilingInputs(
            selling_price=24.99,
            referral_fee_per_unit=3.75,
            fulfillment_fee_per_unit=3.25,
            inbound_cost_per_unit=0.75,
            storage_estimate=0.35,
            return_allowance=1.00,
            ad_allowance=3.00,
            target_profit=5.00,
            supplier_unit_cost=3.40,
            supplier_freight_cost_per_unit=0.85,
            packaging_cost_per_unit=0.65,
        )
    )

    assert result.amazon_fees == 7.00
    assert result.break_even_landed_cost == 12.89
    assert result.max_landed_cost == 7.89
    assert result.supplier_landed_cost == 4.90
    assert result.margin_of_safety == 2.99
    assert result.required_supplier_unit_cost == 6.39
    assert result.decision == "quote_at_or_below_ceiling"


def test_cost_ceiling_can_run_before_supplier_quote() -> None:
    result = calculate_cost_ceiling(
        CostCeilingInputs(
            selling_price=20,
            referral_fee_per_unit=3,
            fulfillment_fee_per_unit=4,
            inbound_cost_per_unit=1,
            storage_estimate=0.5,
            return_allowance=1,
            ad_allowance=2,
            target_profit=4,
        )
    )

    assert result.max_landed_cost == 4.50
    assert result.supplier_landed_cost is None
    assert result.decision == "needs_supplier_quote"
