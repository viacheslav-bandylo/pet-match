from fastapi import APIRouter, Depends, HTTPException

from app.core.engine import RulesEngine
from app.core.models import EvaluateRequest, EvaluateResponse
from app.dependencies import get_rules_engine

router = APIRouter()


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    request: EvaluateRequest,
    engine: RulesEngine = Depends(get_rules_engine),
) -> EvaluateResponse:
    try:
        return engine.evaluate(request)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown pet type: {request.pet_type}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
