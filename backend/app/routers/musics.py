import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Album, Music, Rate
from app.routers.albums import get_album_or_404
from app.schemas import (
    MusicOut,
    Page,
    RateCreate,
    RateListOut,
    RateOut,
    RateSummary,
    RateUpdate,
    page_params,
)
from app.schemas.pagination import PageParams
from app.security.auth import get_current_user
from app.services.rates import get_rates_summary
from app.simulation import SimulationRoute, simulation_params_dependency

router = APIRouter(prefix="/albums/{album_id}/musics", tags=["musics"], route_class=SimulationRoute,
    dependencies=[Depends(simulation_params_dependency)],
)


async def get_music_or_404(
    album: Annotated[Album, Depends(get_album_or_404)],
    music_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Music:
    music = await db.get(Music, music_id)
    if music is None or music.album_id != album.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Music '{music_id}' not found in album '{album.id}'",
        )
    return music


@router.get("", response_model=Page[MusicOut])
async def list_musics(
    album: Annotated[Album, Depends(get_album_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[MusicOut]:
    count_stmt = select(func.count()).select_from(Music).where(
        Music.album_id == album.id
    )
    total = (await db.scalar(count_stmt)) or 0
    musics = (
        await db.scalars(
            select(Music)
            .where(Music.album_id == album.id)
            .order_by(Music.id)
            .offset(params.offset)
            .limit(params.page_size)
        )
    ).all()
    return Page.create(
        [MusicOut.model_validate(m) for m in musics], params, total
    )


@router.get("/{music_id}", response_model=MusicOut)
async def get_music(
    music: Annotated[Music, Depends(get_music_or_404)],
) -> Music:
    return music


@router.get("/{music_id}/rate", response_model=RateListOut)
async def list_music_rates(
    music: Annotated[Music, Depends(get_music_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    params: Annotated[PageParams, Depends(page_params)],
) -> RateListOut:
    total = (
        await db.scalar(
            select(func.count()).select_from(Rate).where(Rate.music_id == music.id)
        )
    ) or 0
    rates = (
        await db.scalars(
            select(Rate)
            .where(Rate.music_id == music.id)
            .order_by(Rate.id)
            .offset(params.offset)
            .limit(params.page_size)
        )
    ).all()
    summary = await get_rates_summary(db, music_id=music.id)
    return RateListOut(
        items=[RateOut.model_validate(r) for r in rates],
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=math.ceil(total / params.page_size) if total else 0,
        summary=RateSummary(**summary),
    )


@router.post(
    "/{music_id}/rate",
    response_model=RateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_music_rate(
    music: Annotated[Music, Depends(get_music_or_404)],
    payload: RateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> Rate:
    rate = Rate(
        album_id=None,
        music_id=music.id,
        rater_name=payload.rater_name,
        rate=payload.rate,
        description=payload.description,
        is_generated=False,
    )
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return rate


async def get_music_rate_or_404(
    music: Annotated[Music, Depends(get_music_or_404)],
    rate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Rate:
    rate = await db.get(Rate, rate_id)
    if rate is None or rate.music_id != music.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate '{rate_id}' not found for music '{music.id}'",
        )
    return rate


@router.put("/{music_id}/rate/{rate_id}", response_model=RateOut)
async def update_music_rate(
    rate: Annotated[Rate, Depends(get_music_rate_or_404)],
    payload: RateUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> Rate:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rate, field, value)
    await db.commit()
    await db.refresh(rate)
    return rate


@router.delete("/{music_id}/rate/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_music_rate(
    rate: Annotated[Rate, Depends(get_music_rate_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> None:
    await db.delete(rate)
    await db.commit()