from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(255), nullable=False)
    music_count: Mapped[int] = mapped_column(Integer, nullable=False)
    release_date: Mapped[date] = mapped_column("releaseDate", Date, nullable=False)
    llm_description: Mapped[str] = mapped_column(String(500), nullable=False)
    llm_emotion_analysis: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_overall_public_reception: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    musics: Mapped[list[Music]] = relationship(  # noqa: F821
        back_populates="album", cascade="all, delete-orphan", passive_deletes=True
    )
    rates: Mapped[list[Rate]] = relationship(  # noqa: F821
        back_populates="album", cascade="all, delete-orphan", passive_deletes=True
    )