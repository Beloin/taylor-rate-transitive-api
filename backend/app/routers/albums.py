import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Album, Rate
from app.schemas import (
    AlbumOut,
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

router = APIRouter(prefix="/albums", tags=["albums"], route_class=SimulationRoute,
    dependencies=[Depends(simulation_params_dependency)],
)


async def get_album_or_404(
    album_id: int, db: Annotated[AsyncSession, Depends(get_db)]
) -> Album:
    album = await db.get(Album, album_id)
    if album is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Album '{album_id}' not found",
        )
    return album


@router.get("", response_model=Page[AlbumOut])
async def list_albums(
    db: Annotated[AsyncSession, Depends(get_db)],
    params: Annotated[PageParams, Depends(page_params)],
) -> Page[AlbumOut]:
    total = (
        await db.scalar(select(func.count()).select_from(Album))
    ) or 0
    albums = (
        await db.scalars(
            select(Album).order_by(Album.id).offset(params.offset).limit(params.page_size)
        )
    ).all()
    return Page.create(
        [AlbumOut.model_validate(a) for a in albums], params, total
    )


@router.get("/{album_id}", response_model=AlbumOut)
async def get_album(
    album: Annotated[Album, Depends(get_album_or_404)],
) -> Album:
    return album


@router.get("/{album_id}/rate", response_model=RateListOut)
async def list_album_rates(
    album: Annotated[Album, Depends(get_album_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    params: Annotated[PageParams, Depends(page_params)],
) -> RateListOut:
    base = select(Rate).where(Rate.album_id == album.id)
    total = (
        await db.scalar(
            select(func.count()).select_from(Rate).where(Rate.album_id == album.id)
        )
    ) or 0
    rates = (
        await db.scalars(
            base.order_by(Rate.id).offset(params.offset).limit(params.page_size)
        )
    ).all()
    summary = await get_rates_summary(db, album_id=album.id)
    return RateListOut(
        items=[RateOut.model_validate(r) for r in rates],
        page=params.page,
        page_size=params.page_size,
        total=total,
        total_pages=math.ceil(total / params.page_size) if total else 0,
        summary=RateSummary(**summary),
    )


@router.post(
    "/{album_id}/rate",
    response_model=RateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_album_rate(
    album: Annotated[Album, Depends(get_album_or_404)],
    payload: RateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> Rate:
    rate = Rate(
        album_id=album.id,
        music_id=None,
        rater_name=payload.rater_name,
        rate=payload.rate,
        description=payload.description,
        is_generated=False,
    )
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    return rate


async def get_album_rate_or_404(
    album: Annotated[Album, Depends(get_album_or_404)],
    rate_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Rate:
    rate = await db.get(Rate, rate_id)
    if rate is None or rate.album_id != album.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate '{rate_id}' not found for album '{album.id}'",
        )
    return rate


@router.put("/{album_id}/rate/{rate_id}", response_model=RateOut)
async def update_album_rate(
    rate: Annotated[Rate, Depends(get_album_rate_or_404)],
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


@router.delete("/{album_id}/rate/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_album_rate(
    rate: Annotated[Rate, Depends(get_album_rate_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[str, Depends(get_current_user)],
) -> None:
    await db.delete(rate)
    await db.commit()