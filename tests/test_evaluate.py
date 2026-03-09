import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compatible_case(client: AsyncClient) -> None:
    resp = await client.post("/evaluate", json={
        "pet_type": "dog",
        "housing": "house",
        "budget_usd": 300,
        "has_children": False,
        "hours_free_per_day": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["compatible"] is True
    assert data["risk_level"] == "low"
    assert data["reasons"] == []
    assert data["alternatives"] == []


@pytest.mark.asyncio
async def test_high_risk_reject(client: AsyncClient) -> None:
    resp = await client.post("/evaluate", json={
        "pet_type": "dog",
        "housing": "apartment",
        "budget_usd": 50,
        "has_children": True,
        "hours_free_per_day": 0.5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["compatible"] is False
    assert data["risk_level"] == "high"
    assert len(data["reasons"]) > 0


@pytest.mark.asyncio
async def test_alternatives_returned(client: AsyncClient) -> None:
    resp = await client.post("/evaluate", json={
        "pet_type": "dog",
        "housing": "apartment",
        "budget_usd": 100,
        "has_children": False,
        "hours_free_per_day": 2,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["compatible"] is False
    alternatives = data["alternatives"]
    assert len(alternatives) > 0
    for alt in alternatives:
        assert "pet_type" in alt
        assert "why" in alt


@pytest.mark.asyncio
async def test_unknown_pet_type(client: AsyncClient) -> None:
    resp = await client.post("/evaluate", json={
        "pet_type": "dragon",
        "housing": "castle",
        "budget_usd": 9999,
        "has_children": False,
        "hours_free_per_day": 24,
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_missing_required_field(client: AsyncClient) -> None:
    resp = await client.post("/evaluate", json={
        "pet_type": "dog",
        "housing": "house",
    })
    assert resp.status_code == 422
