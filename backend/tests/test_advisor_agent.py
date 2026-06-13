"""Advisor agent rule-based fallback (works without LLM credits)."""

from __future__ import annotations

import pytest

from agents.advisor_agent import _try_rule_based_answer


def test_rule_based_highest_demand_question() -> None:
    ctx = {
        "run_id": "83564d17-5517-474c-9cf9-7eb43ab7f9ba",
        "mandi_rows": [
            {
                "name": "Yeshwanthpur APMC",
                "expected_demand_kg": 1200.0,
                "incoming_supply_kg": 800.0,
                "shortage_kg": 400.0,
                "fulfilment_pct": 66.7,
                "status": "SHORTAGE",
            },
            {
                "name": "Hubli APMC",
                "expected_demand_kg": 900.0,
                "incoming_supply_kg": 900.0,
                "shortage_kg": 0.0,
                "fulfilment_pct": 100.0,
                "status": "SUPPLY MET",
            },
        ],
    }
    reply = _try_rule_based_answer("Which mandi has the highest demand this week?", ctx)
    assert reply is not None
    assert "Yeshwanthpur APMC" in reply
    assert "1200" in reply


def test_rule_based_shortage_question() -> None:
    ctx = {
        "run_id": "abc12345-0000-0000-0000-000000000000",
        "mandi_rows": [
            {
                "name": "Mandi A",
                "expected_demand_kg": 500.0,
                "incoming_supply_kg": 100.0,
                "shortage_kg": 400.0,
                "fulfilment_pct": 20.0,
                "status": "CRITICAL SHORTAGE",
            },
        ],
    }
    reply = _try_rule_based_answer("Which mandi has the biggest shortage?", ctx)
    assert reply is not None
    assert "Mandi A" in reply
    assert "400" in reply
