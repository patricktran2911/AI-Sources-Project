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
from app.database.connection import create_pool
from app.database.migrations import run_migrations, seed_from_json
from app.features.registry import FeatureRegistry
from app.features.session_store import SessionStore
from app.orchestration.orchestrator import Orchestrator
from app.prompt.prompt_builder import PromptBuilder
from app.providers.factory import get_provider
from app.repository.knowledge_repo import KnowledgeRepository
from app.core.rate_limiter import RateLimiter
from app.retrieval.embedding_retriever import EmbeddingRetriever
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.bm25_retriever import BM25Retriever
from app.validation.relevance_validator import RelevanceValidator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise heavy components once at startup."""
    settings = get_settings()
    setup_logging(settings.debug)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Database
    pool = await create_pool(settings.database_url)
    await run_migrations(pool)
    await seed_from_json(pool, settings.data_dir)

    # Layers
    knowledge_repo = KnowledgeRepository(pool)
    retriever = EmbeddingRetriever()
    bm25 = BM25Retriever()
    hybrid = HybridRetriever(embedding_retriever=retriever, bm25_retriever=bm25)
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
        hybrid_retriever=hybrid,
    )

    # Attach to app state so routes can access them
    app.state.pool = pool
    app.state.orchestrator = orchestrator
    app.state.context_registry = context_registry
    app.state.feature_registry = feature_registry
    app.state.knowledge_repo = knowledge_repo
    app.state.provider = provider
    app.state.session_store = SessionStore(max_turns=settings.session_max_turns, pool=pool)
    app.state.rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_max_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    logger.info("All layers initialised — server ready")
    yield
    await pool.close()
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

    # Rate-limit middleware — only POST to AI endpoints costs money
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/v1/ai/") and request.method == "POST":
            client_ip = request.client.host if request.client else "unknown"
            if client_ip != "testclient":
                limiter: RateLimiter = request.app.state.rate_limiter
                if not limiter.is_allowed(client_ip):
                    return JSONResponse(
                        status_code=429,
                        content={"success": False, "error": "Rate limit exceeded. Please wait before sending more requests."},
                        headers={"Retry-After": "60"},
                    )
        return await call_next(request)

    # Routes
    app.include_router(health_router, prefix="/api/v1", tags=["system"])
    app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])

    # Serve the chat UI at root
    @app.get("/", include_in_schema=False)
    async def serve_chat_ui():
        return FileResponse(Path(__file__).parent / "static" / "test_chat.html")

    # Serve the full API test lab
    @app.get("/test", include_in_schema=False)
    async def serve_test_lab():
        return FileResponse(Path(__file__).parent / "static" / "test_all.html")

    return app


app = create_app()

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=s.debug)
