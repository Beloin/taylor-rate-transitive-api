from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.db import dispose_engine
from app.routers import albums, auth, musics, setup
from app.services.seed import ensure_seeded
from app.simulation.handlers import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_seeded()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Taylor Music Rating API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(albums.router)
    app.include_router(musics.router)
    app.include_router(setup.router)
    register_error_handlers(app)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()