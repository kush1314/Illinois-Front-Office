from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.data_pipeline.refresh import schedule_background_refresh
from app.db import initialize_database
from app.routes.api import router
from app.services.ml_registry import train_pipeline
from app.services.repository import get_historical, refresh_cache


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title=settings.app_name, version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup_event() -> None:
        # Load real BartTorvik data from CSV → SQLite, train ML, serve immediately
        initialize_database()
        refresh_cache()
        train_pipeline(get_historical())
        # Background refresh disabled: data/players.csv contains real 2024-25 BartTorvik stats
        # (Cooper Flagg, Johni Broome, Braden Smith, etc. from 95 schools).
        # Uncomment the line below to re-scrape, which requires Playwright + barttorvik access.
        # schedule_background_refresh(delay_seconds=15, current_year=2025)

    app.include_router(router)
    return app


app = create_app()
