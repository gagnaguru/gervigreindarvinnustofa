"""Phone bill calculator.

See PROJECT.md for the spec.
"""

from __future__ import annotations

from dataclasses import dataclass


VAT_RATE = 0.24


@dataclass(frozen=True)
class Plan:
    """Monthly tariff (dict-shaped inputs use the same keys as PROJECT.md)."""

    monthly_fee: int
    included_minutes: int
    included_sms: int
    included_gb: float
    overage_per_minute: float
    overage_per_sms: float
    overage_per_gb: float

    @classmethod
    def from_dict(cls, d: dict) -> Plan:
        raise NotImplementedError("Implement Plan.from_dict — see PROJECT.md")


@dataclass(frozen=True)
class Usage:
    """Measured usage for one billing period."""

    minutes: float
    sms: int
    gb: float

    @classmethod
    def from_dict(cls, d: dict) -> Usage:
        raise NotImplementedError("Implement Usage.from_dict — see PROJECT.md")

    def billable_voice_minutes(self) -> float:
        raise NotImplementedError(
            "Implement Usage.billable_voice_minutes — see PROJECT.md"
        )


@dataclass(frozen=True)
class Bill:
    """One computed invoice snapshot (amounts in ISK before/after VAT)."""

    billable_voice_minutes: float
    voice_overage_minutes: float
    sms_overage: int
    gb_overage: float
    subtotal_before_vat: float
    total_with_vat: float


class BillingCalculator:
    """Applies plan rules to usage and produces a ``Bill``."""

    def calculate(self, plan: Plan, usage: Usage) -> Bill:
        raise NotImplementedError(
            "Implement BillingCalculator.calculate — see PROJECT.md"
        )


def calculate_bill(plan: dict, usage: dict) -> float:
    """Dict-shaped entry point; returns total ISK including VAT."""
    raise NotImplementedError("Implement calculate_bill — see README.md")
