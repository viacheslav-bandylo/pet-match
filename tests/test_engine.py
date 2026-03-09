from pathlib import Path

import pytest

from app.core.engine import RulesEngine, _weight_to_risk
from app.core.models import Condition, EvaluateRequest


@pytest.fixture
def cond() -> dict:
    """Base condition kwargs."""
    return {"field": "value", "risk_weight": 1, "reason": "test"}


class TestCheckCondition:
    def test_gte(self, cond: dict) -> None:
        c = Condition(**cond, operator="gte", value=10)
        assert RulesEngine._check_condition(c, {"value": 10}) is True
        assert RulesEngine._check_condition(c, {"value": 9}) is False

    def test_lte(self, cond: dict) -> None:
        c = Condition(**cond, operator="lte", value=10)
        assert RulesEngine._check_condition(c, {"value": 10}) is True
        assert RulesEngine._check_condition(c, {"value": 11}) is False

    def test_eq(self, cond: dict) -> None:
        c = Condition(**cond, operator="eq", value=True)
        assert RulesEngine._check_condition(c, {"value": True}) is True
        assert RulesEngine._check_condition(c, {"value": False}) is False

    def test_neq(self, cond: dict) -> None:
        c = Condition(**cond, operator="neq", value="bad")
        assert RulesEngine._check_condition(c, {"value": "good"}) is True
        assert RulesEngine._check_condition(c, {"value": "bad"}) is False

    def test_in(self, cond: dict) -> None:
        c = Condition(**cond, operator="in", value=["a", "b"])
        assert RulesEngine._check_condition(c, {"value": "a"}) is True
        assert RulesEngine._check_condition(c, {"value": "c"}) is False

    def test_not_in(self, cond: dict) -> None:
        c = Condition(**cond, operator="not_in", value=["x", "y"])
        assert RulesEngine._check_condition(c, {"value": "z"}) is True
        assert RulesEngine._check_condition(c, {"value": "x"}) is False

    def test_missing_field(self, cond: dict) -> None:
        c = Condition(**cond, operator="gte", value=10)
        assert RulesEngine._check_condition(c, {}) is False


class TestRiskLevel:
    def test_zero_is_low(self) -> None:
        assert _weight_to_risk(0) == "low"

    def test_boundary_medium(self) -> None:
        assert _weight_to_risk(1) == "medium"
        assert _weight_to_risk(4) == "medium"

    def test_high(self) -> None:
        assert _weight_to_risk(5) == "high"
        assert _weight_to_risk(10) == "high"


class TestEvaluate:
    def test_missing_profile_field(self, engine: RulesEngine) -> None:
        """Fields not in the profile should be treated as violated conditions."""
        request = EvaluateRequest(
            pet_type="dog",
            housing="house",
            budget_usd=300,
            has_children=False,
            hours_free_per_day=5,
        )
        profile = request.model_dump(exclude={"pet_type"})
        # Remove a field to simulate missing data
        del profile["hours_free_per_day"]

        cond = engine.rules.pets["dog"].conditions[1]  # hours_free_per_day condition
        assert RulesEngine._check_condition(cond, profile) is False
