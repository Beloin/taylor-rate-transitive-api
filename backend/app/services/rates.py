from __future__ import annotations

import random

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Album, Music, Rate
from app.services.seed import get_rate_pool

RATER_NAMES = [
    "John Smith",
    "Emily Davis",
    "Michael Brown",
    "Sarah Johnson",
    "David Wilson",
    "Jessica Taylor",
    "Swiftie_99",
    "MusicLover",
    "CountryFan",
    "PopEnthusiast",
]


async def reset_rates(session: AsyncSession) -> int:
    """Delete all generated rates."""
    result = await session.execute(
        delete(Rate).where(Rate.is_generated.is_(True))
    )
    await session.commit()
    return result.rowcount or 0


async def randomize_rates(
    session: AsyncSession, seed: int, album_rate_count: int, music_rate_count: int
) -> tuple[int, int]:
    """Create random rates for all albums and musics."""
    rng = random.Random(seed) if seed != -1 else random.Random()

    pool = get_rate_pool() or [
        {"rate": 4, "description": "This is pretty good, I liked it."}
    ]

    album_ids = (await session.execute(select(Album.id))).scalars().all()
    music_ids = (await session.execute(select(Music.id))).scalars().all()

    created_album = created_music = 0
    for album_id in album_ids:
        for _ in range(album_rate_count):
            entry = rng.choice(pool)
            session.add(
                Rate(
                    album_id=album_id,
                    music_id=None,
                    rater_name=rng.choice(RATER_NAMES),
                    rate=entry.get("rate", rng.randint(1, 5)),
                    description=entry["description"],
                    is_generated=True,
                )
            )
            created_album += 1
    for music_id in music_ids:
        for _ in range(music_rate_count):
            entry = rng.choice(pool)
            session.add(
                Rate(
                    album_id=None,
                    music_id=music_id,
                    rater_name=rng.choice(RATER_NAMES),
                    rate=entry.get("rate", rng.randint(1, 5)),
                    description=entry["description"],
                    is_generated=True,
                )
            )
            created_music += 1
    await session.commit()
    return created_album, created_music


async def get_rates_summary(
    session: AsyncSession, *, album_id: int | None = None, music_id: int | None = None
) -> dict:
    """Return {count, average} for rates of an album or music."""
    stmt = select(func.count(Rate.id), func.avg(Rate.rate))
    if album_id is not None:
        stmt = stmt.where(Rate.album_id == album_id)
    if music_id is not None:
        stmt = stmt.where(Rate.music_id == music_id)
    count, avg = (await session.execute(stmt)).one()
    return {"count": count, "average": float(avg) if avg is not None else None}