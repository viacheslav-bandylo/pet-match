from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import yaml

from app.core.models import (
    Alternative,
    Condition,
    EvaluateRequest,
    EvaluateResponse,
    RulesConfig, PetConfig,
)

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent.parent / "rules.yaml"


def load_rules(path: Path = DEFAULT_RULES_PATH) -> RulesConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RulesConfig.model_validate(raw)


class RulesEngine:
    def __init__(self, rules_path: Path = DEFAULT_RULES_PATH) -> None:
        self._rules_path = rules_path
        self._rules: RulesConfig = load_rules(rules_path)
        self._lock = asyncio.Lock()

    @property
    def rules(self) -> RulesConfig:
        return self._rules

    async def reload(self) -> RulesConfig:
        new_rules = load_rules(self._rules_path)
        async with self._lock:
            self._rules = new_rules
        return new_rules

    def evaluate(self, request: EvaluateRequest) -> EvaluateResponse:
        rules = self._rules
        pet_key = request.pet_type

        if pet_key not in rules.pets:
            raise KeyError(f"Unknown pet type: {pet_key}")

        pet_config = rules.pets[pet_key]
        profile = request.model_dump(exclude={"pet_type"})

        reasons: list[str] = []
        total_weight = 0.0

        for condition in pet_config.conditions:
            if not self._check_condition(condition, profile):
                reasons.append(condition.reason)
                total_weight += condition.risk_weight

        risk_level = _weight_to_risk(total_weight)
        compatible = risk_level == "low"

        alternatives: list[Alternative] = []
        if not compatible:
            alternatives = self._build_alternatives(pet_config, profile)

        return EvaluateResponse(
            compatible=compatible,
            risk_level=risk_level,
            reasons=reasons,
            alternatives=alternatives,
        )

    @staticmethod
    def _check_condition(condition: Condition, profile: dict[str, Any]) -> bool:
        if condition.field not in profile:
            raise ValueError(
                f"Profile is missing required field '{condition.field}' "
                f"referenced by condition: {condition.reason}"
            )
        value = profile[condition.field]

        op = condition.operator
        expected = condition.value

        if op == "gte":
            return value >= expected
        if op == "lte":
            return value <= expected
        if op == "eq":
            return value == expected
        if op == "neq":
            return value != expected
        if op == "in":
            return value in expected
        if op == "not_in":
            return value not in expected

        return False

    def _build_alternatives(
        self, pet_config: PetConfig, profile: dict[str, Any]
    ) -> list[Alternative]:
        rules = self._rules
        alternatives: list[Alternative] = []

        for alt_key in pet_config.alternatives_if_rejected:
            alt_config = rules.pets.get(alt_key)
            if alt_config is None:
                continue

            failed_reasons: list[str] = []
            total_weight = 0.0
            for cond in alt_config.conditions:
                if not self._check_condition(cond, profile):
                    failed_reasons.append(cond.reason)
                    total_weight += cond.risk_weight

            alt_risk = _weight_to_risk(total_weight)

            if alt_risk == "low":
                why = f"{alt_config.label} подходит вам по всем параметрам"
            elif alt_risk == "medium":
                why = (
                    f"{alt_config.label} — возможный вариант, но есть нюансы: "
                    + "; ".join(failed_reasons)
                )
            else:
                continue

            alternatives.append(Alternative(pet_type=alt_key, why=why))

        return alternatives


def _weight_to_risk(total: float) -> str:
    if total == 0:
        return "low"
    if total <= 4:
        return "medium"
    return "high"
