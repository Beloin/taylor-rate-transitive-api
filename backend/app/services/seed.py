from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Album, Music

logger = logging.getLogger(__name__)

RATE_POOL: list[dict] = []


def get_rate_pool() -> list[dict]:
    """Return the currently loaded rate pool (loaded on startup)."""
    return RATE_POOL


def load_rate_pool() -> None:
    """Load data/randomized_rates/*.json into memory as description pool."""
    global RATE_POOL
    rate_dir = Path(get_settings().data_dir) / "randomized_rates"
    pool = []
    if rate_dir.is_dir():
        for f in sorted(rate_dir.glob("*.json")):
            try:
                pool.append(json.loads(f.read_text()))
            except (OSError, json.JSONDecodeError):
                logger.warning("Failed to load rate pool file %s", f)
    RATE_POOL = pool
    logger.info("Loaded %d rate pool entries", len(RATE_POOL))


def _parse_release_date(raw: str) -> date:
    return date.fromisoformat(raw)


async def seed_data(session: AsyncSession) -> None:
    """Insert-if-not-exists all data on data/albums (runs on every startup)."""
    data_dir = Path(get_settings().data_dir) / "albums"
    if not data_dir.is_dir():
        logger.warning("Album data dir %s not found, skipping seed", data_dir)
        return

    albums_created = musics_created = 0
    for album_dir in sorted(data_dir.iterdir()):
        if not album_dir.is_dir():
            continue
        index_path = album_dir / "index.json"
        if not index_path.exists():
            logger.warning("Missing index.json in %s, skipping", album_dir)
            continue
        raw = json.loads(index_path.read_text())
        album_id = int(raw["id"])

        album = await session.get(Album, album_id)
        if album is None:
            album = Album(
                id=album_id,
                name=raw["name"],
                genre=raw["genre"],
                music_count=raw["music_count"],
                release_date=_parse_release_date(raw["releaseDate"]),
                llm_description=raw["llm_description"],
                llm_emotion_analysis=raw["llm_emotion_analysis"],
                llm_overall_public_reception=raw["llm_overall_public_reception"],
            )
            session.add(album)
            albums_created += 1

        for music_file in sorted(album_dir.glob("music_*.json")):
            mraw = json.loads(music_file.read_text())
            music_id = mraw["id"]
            existing = await session.get(Music, music_id)
            if existing is None:
                session.add(
                    Music(
                        id=music_id,
                        album_id=album_id,
                        name=mraw["name"],
                        genre=mraw["genre"],
                        llm_description=mraw["llm_description"],
                        llm_emotion_analysis=mraw.get("llm_emotion_analysis"),
                    )
                )
                musics_created += 1
    await session.commit()
    logger.info(
        "Seed complete: %d new albums, %d new musics", albums_created, musics_created
    )


async def ensure_seeded() -> None:
    from app.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        await seed_data(session)
    load_rate_pool()