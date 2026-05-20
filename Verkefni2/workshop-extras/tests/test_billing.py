"""Thorough test suite for the phone bill calculator.

Tests derived strictly from PROJECT.md spec. Copy this file into
tests/test_billing.py after the agent generates billing.py:

    cp workshop-extras/tests/test_billing.py tests/test_billing.py
"""

import pytest

from billing import Bill, BillingCalculator, Plan, Usage, calculate_bill


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def standard_plan_dict():
    return {
        "monthly_fee": 4990,
        "included_minutes": 100,
        "included_sms": 100,
        "included_gb": 10.0,
        "overage_per_minute": 15.0,
        "overage_per_sms": 10.0,
        "overage_per_gb": 990.0,
    }


@pytest.fixture
def standard_plan(standard_plan_dict):
    return Plan.from_dict(standard_plan_dict)


@pytest.fixture
def calculator():
    return BillingCalculator()


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

class TestPlan:
    def test_from_dict(self, standard_plan_dict):
        p = Plan.from_dict(standard_plan_dict)
        assert p.monthly_fee == 4990
        assert p.included_minutes == 100
        assert p.included_sms == 100
        assert p.included_gb == 10.0
        assert p.overage_per_minute == 15.0
        assert p.overage_per_sms == 10.0
        assert p.overage_per_gb == 990.0

    def test_frozen(self, standard_plan):
        with pytest.raises(AttributeError):
            standard_plan.monthly_fee = 0


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

class TestUsage:
    def test_from_dict(self):
        u = Usage.from_dict({"minutes": 120.0, "sms": 50, "gb": 12.0})
        assert u.minutes == 120.0
        assert u.sms == 50
        assert u.gb == 12.0

    def test_frozen(self):
        u = Usage(minutes=1.0, sms=0, gb=0.0)
        with pytest.raises(AttributeError):
            u.minutes = 2.0


# ---------------------------------------------------------------------------
# Billable voice minutes — spec Rule 2
# ---------------------------------------------------------------------------

class TestBillableVoiceMinutes:
    """All five spec worked examples plus edge cases."""

    def test_zero_usage(self):
        assert Usage(minutes=0, sms=0, gb=0.0).billable_voice_minutes() == 0

    def test_negative_usage(self):
        """Spec: no voice usage → 0 billable minutes."""
        assert Usage(minutes=-5.0, sms=0, gb=0.0).billable_voice_minutes() == 0

    def test_30_seconds(self):
        """m=0.5 (30 s) → billable = 1 (first whole minute)."""
        assert Usage(minutes=0.5, sms=0, gb=0.0).billable_voice_minutes() == 1

    def test_exactly_one_minute(self):
        """m=1.0 (60 s) → billable = 1."""
        assert Usage(minutes=1.0, sms=0, gb=0.0).billable_voice_minutes() == 1

    def test_90_seconds(self):
        """m=1.5 (90 s) → billable = 1.5."""
        assert Usage(minutes=1.5, sms=0, gb=0.0).billable_voice_minutes() == 1.5

    def test_91_seconds(self):
        """m=91/60 (~91 s) → billable = 2.0."""
        assert Usage(minutes=91 / 60, sms=0, gb=0.0).billable_voice_minutes() == 2.0

    def test_very_short_call(self):
        """Any positive usage → at least 1 billable minute."""
        assert Usage(minutes=0.01, sms=0, gb=0.0).billable_voice_minutes() == 1

    def test_exactly_two_minutes(self):
        """m=2.0 (120 s): r=60, ceil(60/30)=2 → 1+1 = 2."""
        assert Usage(minutes=2.0, sms=0, gb=0.0).billable_voice_minutes() == 2

    def test_two_and_a_half_minutes(self):
        """m=2.5 (150 s): r=90, ceil(90/30)=3 → 1+1.5 = 2.5."""
        assert Usage(minutes=2.5, sms=0, gb=0.0).billable_voice_minutes() == 2.5

    def test_just_over_one_minute(self):
        """61 seconds: first started 30-s step after minute 1 → 1.5."""
        u = Usage(minutes=61 / 60, sms=0, gb=0.0)
        assert u.billable_voice_minutes() == 1.5

    def test_integer_minutes_equal_raw(self):
        """For exact integer minutes the ladder gives back the same number."""
        for m in (1, 2, 3, 5, 10, 60, 120):
            result = Usage(minutes=float(m), sms=0, gb=0.0).billable_voice_minutes()
            assert result == m, f"m={m}: expected {m}, got {result}"


# ---------------------------------------------------------------------------
# Bill frozen
# ---------------------------------------------------------------------------

class TestBill:
    def test_frozen(self):
        b = Bill(
            billable_voice_minutes=1.0,
            voice_overage_minutes=0.0,
            sms_overage=0,
            gb_overage=0.0,
            subtotal_before_vat=4990.0,
            total_with_vat=4990.0 * 1.24,
        )
        with pytest.raises(AttributeError):
            b.total_with_vat = 0.0


# ---------------------------------------------------------------------------
# BillingCalculator
# ---------------------------------------------------------------------------

class TestBillingCalculator:

    def test_zero_usage(self, standard_plan, calculator):
        """Monthly fee charged even with zero usage."""
        usage = Usage(minutes=0, sms=0, gb=0.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.billable_voice_minutes == 0
        assert bill.voice_overage_minutes == 0
        assert bill.sms_overage == 0
        assert bill.gb_overage == 0.0
        assert bill.subtotal_before_vat == 4990
        assert bill.total_with_vat == pytest.approx(6187.6)

    def test_within_included_quota(self, standard_plan, calculator):
        """All usage within plan → no overage, just monthly fee."""
        usage = Usage(minutes=50.0, sms=50, gb=5.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.voice_overage_minutes == 0
        assert bill.sms_overage == 0
        assert bill.gb_overage == 0.0
        assert bill.subtotal_before_vat == 4990
        assert bill.total_with_vat == pytest.approx(6187.6)

    def test_exact_quota_boundary(self, standard_plan, calculator):
        """Usage exactly at included amounts → no overage."""
        usage = Usage(minutes=100.0, sms=100, gb=10.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.voice_overage_minutes == 0
        assert bill.sms_overage == 0
        assert bill.gb_overage == 0.0
        assert bill.subtotal_before_vat == 4990

    def test_spec_example(self, standard_plan, calculator):
        """PROJECT.md example: exact hard-coded values.

        plan fee=4990, included 100min/100sms/10GB
        usage 120min/50sms/12GB
        billable_voice = 120, overage = 20 × 15 = 300
        sms overage = 0, gb overage = 2 × 990 = 1980
        subtotal = 4990 + 300 + 1980 = 7270
        total = 7270 × 1.24 = 9014.8
        """
        usage = Usage(minutes=120.0, sms=50, gb=12.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.billable_voice_minutes == 120
        assert bill.voice_overage_minutes == 20
        assert bill.sms_overage == 0
        assert bill.gb_overage == 2.0
        assert bill.subtotal_before_vat == pytest.approx(7270.0)
        assert bill.total_with_vat == pytest.approx(9014.8)

    def test_voice_overage_hard_coded(self, standard_plan, calculator):
        """Voice-only overage with exact expected ISK."""
        usage = Usage(minutes=120.0, sms=0, gb=0.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.billable_voice_minutes == 120
        assert bill.voice_overage_minutes == 20
        assert bill.subtotal_before_vat == pytest.approx(4990 + 300)
        assert bill.total_with_vat == pytest.approx(5290 * 1.24)

    def test_sms_overage(self, standard_plan, calculator):
        usage = Usage(minutes=0, sms=150, gb=0.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.sms_overage == 50
        assert bill.subtotal_before_vat == pytest.approx(4990 + 500)
        assert bill.total_with_vat == pytest.approx(5490 * 1.24)

    def test_gb_overage(self, standard_plan, calculator):
        usage = Usage(minutes=0, sms=0, gb=12.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.gb_overage == 2.0
        assert bill.subtotal_before_vat == pytest.approx(4990 + 1980)
        assert bill.total_with_vat == pytest.approx(6970 * 1.24)

    def test_fractional_gb_overage(self, standard_plan, calculator):
        """Fractional GB overage is charged proportionally."""
        usage = Usage(minutes=0, sms=0, gb=10.5)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.gb_overage == pytest.approx(0.5)
        assert bill.subtotal_before_vat == pytest.approx(4990 + 495)
        assert bill.total_with_vat == pytest.approx(5485 * 1.24)

    def test_all_overage(self, standard_plan, calculator):
        """Overage on all three dimensions at once."""
        usage = Usage(minutes=120.0, sms=150, gb=12.0)
        bill = calculator.calculate(standard_plan, usage)

        assert bill.voice_overage_minutes == 20
        assert bill.sms_overage == 50
        assert bill.gb_overage == 2.0
        assert bill.subtotal_before_vat == pytest.approx(4990 + 300 + 500 + 1980)
        assert bill.total_with_vat == pytest.approx(7770 * 1.24)

    def test_vat_applied_to_subtotal_not_per_item(self, standard_plan, calculator):
        """VAT is 24% on the pre-VAT subtotal, not per line item."""
        usage = Usage(minutes=120.0, sms=150, gb=12.0)
        bill = calculator.calculate(standard_plan, usage)
        assert bill.total_with_vat == pytest.approx(bill.subtotal_before_vat * 1.24)

    def test_sub_minute_call_overage_uses_billable_not_raw(self, calculator):
        """30-second call with 0 included: raw=0.5, billable=1.0.

        Overage must be 1.0 (billable), not 0.5 (raw).
        """
        plan = Plan(
            monthly_fee=0,
            included_minutes=0,
            included_sms=0,
            included_gb=0.0,
            overage_per_minute=100.0,
            overage_per_sms=0.0,
            overage_per_gb=0.0,
        )
        usage = Usage(minutes=0.5, sms=0, gb=0.0)
        bill = calculator.calculate(plan, usage)

        assert bill.billable_voice_minutes == 1.0
        assert bill.voice_overage_minutes == 1.0
        assert bill.subtotal_before_vat == pytest.approx(100.0)

    def test_91s_call_overage_uses_billable_not_raw(self, calculator):
        """91-second call with 1 included: raw≈1.517, billable=2.0.

        Overage must be 1.0 (billable - included), not ~0.517 (raw - included).
        """
        plan = Plan(
            monthly_fee=0,
            included_minutes=1,
            included_sms=0,
            included_gb=0.0,
            overage_per_minute=60.0,
            overage_per_sms=0.0,
            overage_per_gb=0.0,
        )
        usage = Usage(minutes=91 / 60, sms=0, gb=0.0)
        bill = calculator.calculate(plan, usage)

        assert bill.billable_voice_minutes == 2.0
        assert bill.voice_overage_minutes == 1.0
        assert bill.subtotal_before_vat == pytest.approx(60.0)


# ---------------------------------------------------------------------------
# calculate_bill convenience function
# ---------------------------------------------------------------------------

class TestCalculateBill:
    def test_spec_example_exact(self, standard_plan_dict):
        """PROJECT.md example: total must be 9014.8 ISK."""
        total = calculate_bill(standard_plan_dict, {"minutes": 120, "sms": 50, "gb": 12.0})
        assert total == pytest.approx(9014.8)

    def test_matches_object_path(self, standard_plan_dict):
        """Both paths must give the same result."""
        usage_dict = {"minutes": 120, "sms": 50, "gb": 12.0}
        total = calculate_bill(standard_plan_dict, usage_dict)
        bill = BillingCalculator().calculate(
            Plan.from_dict(standard_plan_dict),
            Usage.from_dict(usage_dict),
        )
        assert bill.total_with_vat == total

    def test_zero_usage(self, standard_plan_dict):
        """Zero usage → just monthly fee + VAT = 6187.6."""
        total = calculate_bill(standard_plan_dict, {"minutes": 0, "sms": 0, "gb": 0.0})
        assert total == pytest.approx(6187.6)

    def test_within_quota(self, standard_plan_dict):
        """Under quota → same as zero overage = 6187.6."""
        total = calculate_bill(
            standard_plan_dict, {"minutes": 50.0, "sms": 50, "gb": 5.0}
        )
        assert total == pytest.approx(6187.6)


# ---------------------------------------------------------------------------
# Input validation — spec says "Usage values are expected to be non-negative"
# ---------------------------------------------------------------------------

class TestNegativeUsageValidation:
    """Negative usage values must raise ValueError."""

    def test_negative_minutes(self, standard_plan_dict):
        with pytest.raises(ValueError):
            calculate_bill(standard_plan_dict, {"minutes": -1, "sms": 0, "gb": 0.0})

    def test_negative_sms(self, standard_plan_dict):
        with pytest.raises(ValueError):
            calculate_bill(standard_plan_dict, {"minutes": 0, "sms": -1, "gb": 0.0})

    def test_negative_gb(self, standard_plan_dict):
        with pytest.raises(ValueError):
            calculate_bill(standard_plan_dict, {"minutes": 0, "sms": 0, "gb": -1.0})
