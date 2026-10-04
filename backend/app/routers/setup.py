from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import (
    RandomizeRequest,
    RandomizeResponse,
    ResetRatesResponse,
)
from app.security.auth import get_current_user
from app.security.cert import cert_paths
from app.services.rates import randomize_rates, reset_rates
from app.simulation import SimulationRoute, simulation_params_dependency

router = APIRouter(prefix="/setup", tags=["setup"], route_class=SimulationRoute,
    dependencies=[Depends(simulation_params_dependency)],
)


@router.post("/reset-rates", response_model=ResetRatesResponse)
async def reset(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> ResetRatesResponse:
    deleted = await reset_rates(db)
    return ResetRatesResponse(
        message=f"Deleted {deleted} generated rates",
        deleted=deleted,
    )


@router.post("/randomize-rates", response_model=RandomizeResponse)
async def randomize(
    payload: RandomizeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> RandomizeResponse:
    created_album, created_music = await randomize_rates(
        db,
        seed=payload.seed,
        album_rate_count=payload.album_rate_count,
        music_rate_count=payload.music_rate_count,
    )
    return RandomizeResponse(
        created_album_rates=created_album,
        created_music_rates=created_music,
    )


@router.get("/cert")
async def get_cert() -> Response:
    cert_path, _ = cert_paths()
    content = cert_path.read_bytes()
    return Response(
        content=content,
        media_type="application/x-pem-file",
        headers={"Content-Disposition": 'attachment; filename="cert.pem"'},
    )