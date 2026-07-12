from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    backtests,
    discovery,
    health,
    ingestion,
    opportunities,
    plugins,
    products,
    security,
    validation,
)
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.security.runtime import validate_runtime_security
from app.services.discovery_worker import recover_discovery_runs

settings = get_settings()
configure_logging(settings.log_level)
validate_runtime_security(settings)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    if (
        settings.discovery_recover_on_startup
        and not getattr(app_instance.state, "disable_discovery_recovery", False)
    ):
        recover_discovery_runs()
    yield


app = FastAPI(title="Product Discovery Terminal", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(products.router)
app.include_router(opportunities.router)
app.include_router(plugins.router)
app.include_router(ingestion.router)
app.include_router(discovery.router)
app.include_router(security.router)
app.include_router(validation.router)
app.include_router(backtests.router)
