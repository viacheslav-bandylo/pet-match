from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- Rules config models ---

class Condition(BaseModel):
    field: str
    operator: Literal["gte", "lte", "eq", "neq", "in", "not_in"]
    value: int | float | str | list | bool
    risk_weight: float = Field(ge=0)
    reason: str


class PetConfig(BaseModel):
    label: str
    group: str
    conditions: list[Condition]
    alternatives_if_rejected: list[str] = []


class RulesConfig(BaseModel):
    version: str
    pets: dict[str, PetConfig]


# --- API models ---

class EvaluateRequest(BaseModel):
    pet_type: str
    housing: str
    budget_usd: float
    has_children: bool
    hours_free_per_day: float


class Alternative(BaseModel):
    pet_type: str
    why: str


class EvaluateResponse(BaseModel):
    compatible: bool
    risk_level: Literal["low", "medium", "high"]
    reasons: list[str]
    alternatives: list[Alternative]


class ReloadResponse(BaseModel):
    version: str
    pets_loaded: int
