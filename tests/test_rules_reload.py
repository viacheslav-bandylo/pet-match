from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.engine import RulesEngine


@pytest.mark.asyncio
async def test_reload_success(client: AsyncClient, engine: RulesEngine, rules_path: Path) -> None:
    updated = rules_path.read_text().replace('version: "1.0.0"', 'version: "2.0.0"')
    rules_path.write_text(updated, encoding="utf-8")

    resp = await client.post("/rules/reload")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0.0"
    assert data["pets_loaded"] == 4


@pytest.mark.asyncio
async def test_reload_invalid_keeps_old(client: AsyncClient, engine: RulesEngine, rules_path: Path) -> None:
    old_version = engine.rules.version

    rules_path.write_text("invalid: [yaml: {broken", encoding="utf-8")

    resp = await client.post("/rules/reload")
    assert resp.status_code == 422

    assert engine.rules.version == old_version
