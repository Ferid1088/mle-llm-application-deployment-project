"""Reference FastAPI application."""

import logging

from fastapi import FastAPI, HTTPException

from solution.deployment_project.config import settings
from solution.deployment_project.models import GenerateRequest, GenerateResponse
from solution.deployment_project.provider import build_provider
from solution.deployment_project.service import GenerationService

logger = logging.getLogger(__name__)

app = FastAPI(title="Northstar LLM Deployment Project")
service = GenerationService(build_provider(settings), settings)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready", "provider": settings.provider, "model": settings.model}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    try:
        return await service.generate(request)
    except Exception as exc:
        logger.exception("Generation provider failed")
        raise HTTPException(
            status_code=502,
            detail="Generation provider unavailable",
        ) from exc
