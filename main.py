"""FastAPI entry point — wires all layers together at startup."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api.ai_routes import router as ai_router
from app.api.health import router as health_router
from app.contexts.context_registry import ContextRegistry
from app.contexts.context_router import ContextRouter
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.features.registry import FeatureRegistry
from app.features.session_store import SessionStore
from app.orchestration.orchestrator import Orchestrator
from app.prompt.prompt_builder import PromptBuilder
from app.providers.factory import get_provider
from app.repository.knowledge_repo import KnowledgeRepository
from app.retrieval.embedding_retriever import EmbeddingRetriever
from app.validation.relevance_validator import RelevanceValidator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy components once at startup."""
    settings = get_settings()
    setup_logging(settings.debug)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Layers
    knowledge_repo = KnowledgeRepository()
    retriever = EmbeddingRetriever()
    validator = RelevanceValidator()
    prompt_builder = PromptBuilder()
    provider = get_provider()
    context_registry = ContextRegistry()
    feature_registry = FeatureRegistry(provider=provider, prompt_builder=prompt_builder)

    orchestrator = Orchestrator(
        context_registry=context_registry,
        feature_registry=feature_registry,
        knowledge_repo=knowledge_repo,
        retriever=retriever,
        validator=validator,
        context_router=ContextRouter(
            context_registry=context_registry,
            knowledge_repo=knowledge_repo,
            retriever=retriever,
        ),
    )

    # Attach to app state so routes can access them
    app.state.orchestrator = orchestrator
    app.state.context_registry = context_registry
    app.state.feature_registry = feature_registry
    app.state.session_store = SessionStore()

    logger.info("All layers initialised — server ready")
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global error handler
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.message},
        )

    # Routes
    app.include_router(health_router, prefix="/api/v1", tags=["system"])
    app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])

    # Serve the chat UI at root
    @app.get("/", include_in_schema=False)
    async def serve_chat_ui():
        return FileResponse(Path(__file__).parent / "static" / "test_chat.html")

    return app


app = create_app()

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=s.debug)
