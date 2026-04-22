from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import analytics_router, documents_router, query_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    logger.info(
        "DocuMind API starting (llm=%s, embed=%s, ollama=%s)",
        settings.llm_model,
        settings.embedding_model,
        settings.ollama_base_url,
    )

    from app.services.evaluator import EvaluatorService
    evaluator = EvaluatorService(
        db_path=settings.db_path,
        ollama_base_url=settings.ollama_base_url,
        llm_model=settings.llm_model,
    )
    await evaluator.initialize()

    yield

    logger.info("DocuMind API shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Production RAG engine — fully local, no cloud APIs. "
            "Hybrid search (Qdrant), knowledge graphs (Neo4j), RAGAS evaluation."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> Dict[str, Any]:
        cfg = get_settings()
        ollama_ok = False
        available_models: list = []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{cfg.ollama_base_url}/api/tags")
                if r.status_code == 200:
                    ollama_ok = True
                    data = r.json()
                    available_models = [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

        return {
            "status": "healthy" if ollama_ok else "degraded",
            "service": cfg.app_name,
            "version": cfg.app_version,
            "ollama": {
                "reachable": ollama_ok,
                "url": cfg.ollama_base_url,
                "llm_model": cfg.llm_model,
                "embedding_model": cfg.embedding_model,
                "available_models": available_models,
            },
        }

    @app.get("/", tags=["system"])
    async def root() -> Dict[str, Any]:
        cfg = get_settings()
        return {
            "name": cfg.app_name,
            "version": cfg.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again."},
        )

    return app


app = create_app()
