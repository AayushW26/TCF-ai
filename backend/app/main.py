"""
TCF-ai (Munim.ai) — FastAPI Application Entry Point

WhatsApp-first GST compliance co-pilot for Indian MSMEs.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.services.supabase_client import init_supabase, close_supabase
from app.services.redis_client import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Initialise shared resources on startup; tear down on shutdown."""
    settings = get_settings()

    # ── Startup ───────────────────────────────────────────
    init_supabase(settings.supabase_url, settings.supabase_service_key)
    await init_redis(settings.redis_url)

    yield

    # ── Shutdown ──────────────────────────────────────────
    await close_redis()
    close_supabase()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    application = FastAPI(
        title="TCF-ai API",
        description="WhatsApp-first GST compliance co-pilot for Indian MSMEs",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── CORS ──────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────
    from app.api.auth import router as auth_router
    from app.api.webhook import router as webhook_router
    from app.api.dashboard import router as dashboard_router
    from app.api.gstr2b import router as gstr2b_router
    from app.api.reports import router as reports_router
    from app.api.communications import router as comms_router
    from app.api.email_webhook import router as email_router

    application.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    application.include_router(webhook_router, prefix="/api/v1/webhook", tags=["WhatsApp"])
    application.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
    application.include_router(gstr2b_router, prefix="/api/v1/gstr2b", tags=["GSTR-2B"])
    application.include_router(reports_router, prefix="/api/v1/dashboard/reports", tags=["Reports"])
    application.include_router(comms_router, prefix="/api/v1/communications", tags=["Communications"])
    application.include_router(email_router, prefix="/api/v1/email-webhook", tags=["Email"])

    # ── Health Check ──────────────────────────────────────
    @application.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "tcf-ai-backend"}

    return application


app = create_app()
