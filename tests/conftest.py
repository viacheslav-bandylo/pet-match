from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.engine import RulesEngine
from app.dependencies import get_rules_engine
from app.main import app

SAMPLE_RULES = """\
version: "1.0.0"
pets:
  dog:
    label: "Собака"
    group: domestic
    conditions:
      - field: budget_usd
        operator: gte
        value: 200
        risk_weight: 3
        reason: "Собака требует от $200/мес"
      - field: hours_free_per_day
        operator: gte
        value: 3
        risk_weight: 4
        reason: "Собака требует минимум 3 часа внимания"
      - field: housing
        operator: in
        value: ["house", "apartment_with_yard"]
        risk_weight: 2
        reason: "Собакам нужно пространство"
    alternatives_if_rejected: [cat, hamster]

  cat:
    label: "Кошка"
    group: domestic
    conditions:
      - field: budget_usd
        operator: gte
        value: 80
        risk_weight: 2
        reason: "Кошка требует от $80/мес"
      - field: hours_free_per_day
        operator: gte
        value: 1
        risk_weight: 1
        reason: "Кошке нужен минимум 1 час внимания"
      - field: has_children
        operator: eq
        value: false
        risk_weight: 1
        reason: "Кошки плохо уживаются с детьми"
    alternatives_if_rejected: [hamster, fish]

  hamster:
    label: "Хомяк"
    group: small
    conditions:
      - field: budget_usd
        operator: gte
        value: 20
        risk_weight: 1
        reason: "Минимальный бюджет для хомяка — $20/мес"
      - field: hours_free_per_day
        operator: gte
        value: 0.5
        risk_weight: 1
        reason: "Хомяку нужно 30 минут внимания"
    alternatives_if_rejected: [fish]

  fish:
    label: "Рыбка"
    group: aquatic
    conditions:
      - field: budget_usd
        operator: gte
        value: 30
        risk_weight: 1
        reason: "Аквариум требует от $30/мес"
    alternatives_if_rejected: [hamster]
"""


@pytest.fixture
def rules_path(tmp_path: Path) -> Path:
    p = tmp_path / "rules.yaml"
    p.write_text(SAMPLE_RULES, encoding="utf-8")
    return p


@pytest.fixture
def engine(rules_path: Path) -> RulesEngine:
    return RulesEngine(rules_path=rules_path)


@pytest_asyncio.fixture
async def client(engine: RulesEngine) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_rules_engine] = lambda: engine
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
