"""Phone bill calculator.

See PROJECT.md for the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


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
        return cls(
            monthly_fee=d["monthly_fee"],
            included_minutes=d["included_minutes"],
            included_sms=d["included_sms"],
            included_gb=d["included_gb"],
            overage_per_minute=d["overage_per_minute"],
            overage_per_sms=d["overage_per_sms"],
            overage_per_gb=d["overage_per_gb"],
        )


@dataclass(frozen=True)
class Usage:
    """Measured usage for one billing period."""

    minutes: float
    sms: int
    gb: float

    @classmethod
    def from_dict(cls, d: dict) -> Usage:
        minutes = d["minutes"]
        sms = d["sms"]
        gb = d["gb"]
        if minutes < 0 or sms < 0 or gb < 0:
            raise ValueError("Usage values must be non-negative")
        return cls(minutes=minutes, sms=sms, gb=gb)

    def billable_voice_minutes(self) -> float:
        if self.minutes <= 0:
            return 0.0

        remaining_minutes = max(0.0, self.minutes - 1.0)
        started_half_minute_blocks = math.ceil(remaining_minutes / 0.5)
        return 1.0 + (started_half_minute_blocks * 0.5)


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
        billable_voice_minutes = usage.billable_voice_minutes()
        voice_overage_minutes = max(0.0, billable_voice_minutes - plan.included_minutes)
        sms_overage = max(0, usage.sms - plan.included_sms)
        gb_overage = max(0.0, usage.gb - plan.included_gb)

        subtotal_before_vat = (
            plan.monthly_fee
            + (voice_overage_minutes * plan.overage_per_minute)
            + (sms_overage * plan.overage_per_sms)
            + (gb_overage * plan.overage_per_gb)
        )
        total_with_vat = subtotal_before_vat * (1.0 + VAT_RATE)

        return Bill(
            billable_voice_minutes=billable_voice_minutes,
            voice_overage_minutes=voice_overage_minutes,
            sms_overage=sms_overage,
            gb_overage=gb_overage,
            subtotal_before_vat=subtotal_before_vat,
            total_with_vat=total_with_vat,
        )


def calculate_bill(plan: dict, usage: dict) -> float:
    """Dict-shaped entry point; returns total ISK including VAT."""
    parsed_plan = Plan.from_dict(plan)
    parsed_usage = Usage.from_dict(usage)
    bill = BillingCalculator().calculate(parsed_plan, parsed_usage)
    return bill.total_with_vat
