"""Aplicação FastAPI — AF Copilot AI Backend.

Executar: uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.v1.router import router as v1_router
from .core.config import get_settings
from .core.database import init_db
from .core.logging import configure_logging, get_logger
from .core.security import configure_cors, ensure_auth_token
from .repositories.audit_repository import build_repositories
from .schemas.responses import HealthResponse
from .services.admin_insights import AdminInsightsService
from .services.rag_service import RAGService
from .services.vision_service import VisionService

logger = get_logger(__name__)

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()

    # Token local escrito uma vez; o Electron o lê na inicialização.
    ensure_auth_token()
    init_db()
    logger.info("Serviço %s v%s iniciado", settings.app_name, __version__)

    audit, cache = build_repositories()
    app.state.settings = settings
    app.state.audit = audit
    app.state.cache = cache
    app.state.rag = RAGService(settings)
    app.state.vision = VisionService(settings)
    app.state.insights = AdminInsightsService(settings)

    yield
    logger.info("Serviço encerrado")


app = FastAPI(
    title="AF Copilot AI Backend",
    version=__version__,
    lifespan=lifespan,
    docs_url=None if get_settings().environment == "production" else "/docs",
    redoc_url=None,
)

configure_cors(app)
app.include_router(v1_router)


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        vector_store_ready=request.app.state.rag.is_ready(),
    )


@app.exception_handler(Exception)
async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
    """Evita vazar stack traces/ detalhes internos (OWASP A05)."""
    logger.exception("Erro não tratado: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno. Consulte os logs do servidor."},
    )
