# Phone Bill Calculator

Nova's billing team needs a small billing module that turns a customer's
monthly plan and their actual usage into the amount they should be charged.

## Background

Every month, each customer is on a **plan** that includes a fixed monthly
fee and a bundle of included minutes, SMS, and mobile data. If the
customer exceeds any of these included amounts, they pay an overage rate
for each unit above the limit. The final bill includes **VAT**.

## What the module must provide

Implement the following in **`billing.py`**. All monetary amounts are in
ISK (Icelandic króna).

### Plan

Represents a customer's monthly tariff. Fields:

- `monthly_fee` — fixed monthly charge in ISK
- `included_minutes` — voice minutes included in the plan
- `included_sms` — SMS messages included
- `included_gb` — mobile data included, in gigabytes
- `overage_per_minute` — ISK charged per billable minute beyond included
- `overage_per_sms` — ISK charged per SMS beyond included
- `overage_per_gb` — ISK charged per GB of overage

Plans should be immutable once created. Provide a `Plan.from_dict(d)`
class method to create a plan from a dictionary with the same keys.

### Usage

Represents a customer's actual usage for one billing period. Fields:

- `minutes` — voice usage this month in minutes (may be fractional)
- `sms` — number of SMS messages sent
- `gb` — mobile data used in gigabytes

Usage should be immutable. Provide a `Usage.from_dict(d)` class method.
Usage values are expected to be non-negative.

Provide a `billable_voice_minutes()` method that converts raw voice
usage into billable minutes according to the voice billing rules below.
This method should only handle voice billing logic — not SMS, data, or
fees.

### Bill

A read-only snapshot of one billing calculation. Must include at least:

- `billable_voice_minutes` — the result of the voice billing calculation
- `voice_overage_minutes` — billable minutes charged beyond the plan's included quota
- `sms_overage` — SMS count beyond included
- `gb_overage` — GB beyond included
- `subtotal_before_vat` — monthly fee plus all overage charges, before tax
- `total_with_vat` — the subtotal with VAT added

### BillingCalculator

A class with a `calculate(plan, usage)` method that applies all the
billing rules and returns a `Bill`.

### calculate_bill(plan, usage)

A convenience function for callers that still work with plain
dictionaries. It should parse the dicts into `Plan` and `Usage`,
run the calculator, and return the total amount including VAT.

---

## Billing rules

1. **The monthly fee is always charged**, even if the customer used
   nothing at all.

2. **Voice billing** — calls are not billed at simple clock time.

   - If the customer made no calls, billable minutes is zero.
   - If the customer made any calls at all:
     - The **first whole minute** is always charged (covers the first
       60 seconds).
     - After that first minute, any remaining time is charged in
       **30-second increments**. Each started 30-second block counts
       as half a billable minute.
   - The plan's included minutes are not charged extra. If the customer
     exceeds their included minutes, the excess is charged at the overage
     rate.

3. **SMS and data** — if the customer exceeds their included amount,
   the excess is charged at the overage rate.

4. **VAT** — applicable VAT is added to the bill.

## Example

```python
plan = {
    "monthly_fee": 4990,
    "included_minutes": 100,
    "included_sms": 100,
    "included_gb": 10.0,
    "overage_per_minute": 15.0,
    "overage_per_sms": 10.0,
    "overage_per_gb": 990.0,
}

usage = {"minutes": 120, "sms": 50, "gb": 12.0}

total = calculate_bill(plan, usage)
# total is the full ISK amount the customer owes, including VAT

# Object-oriented path:
b = BillingCalculator().calculate(Plan.from_dict(plan), Usage.from_dict(usage))
assert b.total_with_vat == total
```
