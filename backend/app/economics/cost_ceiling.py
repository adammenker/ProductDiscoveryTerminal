from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

QuoteDecision = Literal["needs_supplier_quote", "quote_at_or_below_ceiling", "quote_above_ceiling"]


@dataclass(frozen=True)
class CostCeilingInputs:
    selling_price: float
    referral_fee_per_unit: float
    fulfillment_fee_per_unit: float
    inbound_cost_per_unit: float
    storage_estimate: float
    return_allowance: float
    ad_allowance: float
    target_profit: float
    supplier_unit_cost: float | None = None
    supplier_freight_cost_per_unit: float | None = None
    packaging_cost_per_unit: float | None = None


@dataclass(frozen=True)
class CostCeilingResult:
    selling_price: float
    amazon_fees: float
    referral_fee_per_unit: float
    fulfillment_fee_per_unit: float
    inbound_cost_per_unit: float
    storage_estimate: float
    return_allowance: float
    ad_allowance: float
    target_profit: float
    break_even_landed_cost: float
    max_landed_cost: float
    supplier_landed_cost: float | None
    required_supplier_unit_cost: float | None
    margin_of_safety: float | None
    margin_of_safety_percent: float | None
    estimated_profit_after_allowances: float | None
    estimated_profit_margin_after_allowances: float | None
    target_profit_margin: float
    decision: QuoteDecision

    def as_dict(self) -> dict[str, float | str | None]:
        return {
            "selling_price": self.selling_price,
            "amazon_fees": self.amazon_fees,
            "referral_fee_per_unit": self.referral_fee_per_unit,
            "fulfillment_fee_per_unit": self.fulfillment_fee_per_unit,
            "inbound_cost_per_unit": self.inbound_cost_per_unit,
            "storage_estimate": self.storage_estimate,
            "return_allowance": self.return_allowance,
            "ad_allowance": self.ad_allowance,
            "target_profit": self.target_profit,
            "break_even_landed_cost": self.break_even_landed_cost,
            "max_landed_cost": self.max_landed_cost,
            "supplier_landed_cost": self.supplier_landed_cost,
            "required_supplier_unit_cost": self.required_supplier_unit_cost,
            "margin_of_safety": self.margin_of_safety,
            "margin_of_safety_percent": self.margin_of_safety_percent,
            "estimated_profit_after_allowances": self.estimated_profit_after_allowances,
            "estimated_profit_margin_after_allowances": self.estimated_profit_margin_after_allowances,
            "target_profit_margin": self.target_profit_margin,
            "decision": self.decision,
        }


def calculate_cost_ceiling(inputs: CostCeilingInputs) -> CostCeilingResult:
    selling_price = _decimal(inputs.selling_price)
    referral_fee = _decimal(inputs.referral_fee_per_unit)
    fulfillment_fee = _decimal(inputs.fulfillment_fee_per_unit)
    inbound_cost = _decimal(inputs.inbound_cost_per_unit)
    storage = _decimal(inputs.storage_estimate)
    returns = _decimal(inputs.return_allowance)
    ads = _decimal(inputs.ad_allowance)
    target_profit = _decimal(inputs.target_profit)
    packaging = _optional_decimal(inputs.packaging_cost_per_unit)
    supplier_unit = _optional_decimal(inputs.supplier_unit_cost)
    supplier_freight = _optional_decimal(inputs.supplier_freight_cost_per_unit)

    amazon_fees = referral_fee + fulfillment_fee
    break_even_landed_cost = selling_price - amazon_fees - inbound_cost - storage - returns - ads
    max_landed_cost = break_even_landed_cost - target_profit

    supplier_landed_cost: Decimal | None = None
    if supplier_unit is not None:
        supplier_landed_cost = supplier_unit + (supplier_freight or Decimal("0")) + (packaging or Decimal("0"))

    required_supplier_unit_cost: Decimal | None = None
    if supplier_freight is not None or packaging is not None:
        required_supplier_unit_cost = max_landed_cost - (supplier_freight or Decimal("0")) - (
            packaging or Decimal("0")
        )

    margin_of_safety: Decimal | None = None
    margin_of_safety_percent: Decimal | None = None
    estimated_profit: Decimal | None = None
    estimated_profit_margin: Decimal | None = None
    decision: QuoteDecision = "needs_supplier_quote"
    if supplier_landed_cost is not None:
        margin_of_safety = max_landed_cost - supplier_landed_cost
        estimated_profit = break_even_landed_cost - supplier_landed_cost
        estimated_profit_margin = _percent(estimated_profit, selling_price)
        decision = (
            "quote_at_or_below_ceiling"
            if supplier_landed_cost <= max_landed_cost
            else "quote_above_ceiling"
        )
        if max_landed_cost > 0:
            margin_of_safety_percent = _percent(margin_of_safety, max_landed_cost)

    return CostCeilingResult(
        selling_price=_money(selling_price),
        amazon_fees=_money(amazon_fees),
        referral_fee_per_unit=_money(referral_fee),
        fulfillment_fee_per_unit=_money(fulfillment_fee),
        inbound_cost_per_unit=_money(inbound_cost),
        storage_estimate=_money(storage),
        return_allowance=_money(returns),
        ad_allowance=_money(ads),
        target_profit=_money(target_profit),
        break_even_landed_cost=_money(break_even_landed_cost),
        max_landed_cost=_money(max_landed_cost),
        supplier_landed_cost=_money(supplier_landed_cost) if supplier_landed_cost is not None else None,
        required_supplier_unit_cost=(
            _money(required_supplier_unit_cost) if required_supplier_unit_cost is not None else None
        ),
        margin_of_safety=_money(margin_of_safety) if margin_of_safety is not None else None,
        margin_of_safety_percent=(
            _ratio(margin_of_safety_percent) if margin_of_safety_percent is not None else None
        ),
        estimated_profit_after_allowances=(
            _money(estimated_profit) if estimated_profit is not None else None
        ),
        estimated_profit_margin_after_allowances=(
            _ratio(estimated_profit_margin) if estimated_profit_margin is not None else None
        ),
        target_profit_margin=_ratio(_percent(target_profit, selling_price)),
        decision=decision,
    )


def _decimal(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: float | int | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


def _percent(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return (numerator / denominator) * Decimal("100")


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _ratio(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

