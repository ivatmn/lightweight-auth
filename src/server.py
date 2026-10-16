# src/server.py
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

# from src.api.login_api import auth_router
from src.core.database import init_db, seed_default_admin


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    await seed_default_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        debug=True,
        docs_url="/docs",
        lifespan=lifespan,
        title="UFS - Auth Service",
        description="Service for authentication and authorization of users",
        version="D-001.001.00",
    )
    # app.include_router(auth_router)
    return app
