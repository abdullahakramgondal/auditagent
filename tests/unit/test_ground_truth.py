import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from data.generator.ground_truth import expected_late_penalty

TOTAL = Decimal("10000000")
FLAT = {"clause_type": "late_penalty", "deadline": "2026-10-15", "mode": "flat_percent", "percent": "10"}
PER_DAY = {
    "clause_type": "late_penalty",
    "deadline": "2026-10-15",
    "mode": "per_day_percent",
    "percent": "1",
    "cap_percent": "10",
}


def test_on_time_has_no_penalty():
    assert expected_late_penalty(FLAT, TOTAL, date(2026, 10, 14)) == 0


def test_per_day_is_capped():
    # 15 days late at 1% per day would be 15%, cap makes it 10%
    assert expected_late_penalty(PER_DAY, TOTAL, date(2026, 10, 30)) == Decimal("1000000")


def test_flat_penalty_inside_grace_is_zero():
    rule = {**FLAT, "grace_days": 3}
    assert expected_late_penalty(rule, TOTAL, date(2026, 10, 17)) == 0


def test_per_day_counts_only_days_after_grace():
    rule = {**PER_DAY, "grace_days": 3}
    # 5 days late, 3 are free, 2 counted at 1% = 2% of 10,000,000
    assert expected_late_penalty(rule, TOTAL, date(2026, 10, 20)) == Decimal("200000")


def test_case_001_expected_matches_independent_calc():
    spec = json.loads(
        (Path(__file__).resolve().parents[2] / "data" / "specs" / "case_001.json").read_text()
    )
    total = Decimal(spec["invoice"]["total_amount"])
    delivered = date.fromisoformat(spec["invoice"]["delivery_date"])
    penalty = expected_late_penalty(spec["rules"][0], total, delivered)
    assert total - penalty == Decimal(spec["expected"]["correct_payable"])
    assert penalty == Decimal(spec["expected"]["total_difference"])