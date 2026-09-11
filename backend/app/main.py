from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import init_engine
from app.core.http import close_http_client
from app.core.logging import configure_logging
from app.seed import seed


def _ensure_columns(sync_conn) -> None:
    from app.core.schema_patch import ensure_event_state_columns

    ensure_event_state_columns(sync_conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    init_engine(settings.database_url)
    from app.core.db import Base, engine
    from app import models  # noqa: F401

    if engine is not None:
        async with engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                try:
                    await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
                except Exception:
                    import structlog

                    structlog.get_logger().warning("pgvector_extension_skipped")
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_ensure_columns)
        try:
            await seed()
        except Exception:
            import structlog

            structlog.get_logger().exception("seed_failed")
        try:
            from app.api.routes import worker

            await worker.resume_unfinished()
        except Exception:
            import structlog

            structlog.get_logger().exception("resume_jobs_failed")
    yield
    await close_http_client()


def create_app() -> FastAPI:
    settings = get_settings()
    origins = settings.cors_origin_list()
    app = FastAPI(title="EventOS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
