from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.evaluate import router as evaluate_router
from app.api.rules import router as rules_router
from app.dependencies import init_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_engine()
    yield


app = FastAPI(title="Pet Compatibility Service", lifespan=lifespan)

app.include_router(evaluate_router)
app.include_router(rules_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
