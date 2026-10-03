from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Music(Base):
    __tablename__ = "musics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(255), nullable=False)
    llm_description: Mapped[str] = mapped_column(String(500), nullable=False)
    llm_emotion_analysis: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    album: Mapped[Album] = relationship(  # noqa: F821
        back_populates="musics"
    )
    rates: Mapped[list[Rate]] = relationship(  # noqa: F821
        back_populates="music", cascade="all, delete-orphan", passive_deletes=True
    )