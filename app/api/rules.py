from fastapi import APIRouter, Depends, HTTPException

from app.core.engine import RulesEngine
from app.core.models import ReloadResponse
from app.dependencies import get_rules_engine

router = APIRouter(prefix="/rules")


@router.post("/reload", response_model=ReloadResponse)
async def reload_rules(
    engine: RulesEngine = Depends(get_rules_engine),
) -> ReloadResponse:
    try:
        new_rules = await engine.reload()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid rules: {exc}")

    return ReloadResponse(
        version=new_rules.version,
        pets_loaded=len(new_rules.pets),
    )
