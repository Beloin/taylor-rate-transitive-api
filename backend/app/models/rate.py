from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Rate(Base):
    __tablename__ = "rates"
    __table_args__ = (
        CheckConstraint(
            "(album_id IS NOT NULL AND music_id IS NULL) "
            "OR (album_id IS NULL AND music_id IS NOT NULL)",
            name="ck_rate_target",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    album_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=True
    )
    music_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("musics.id", ondelete="CASCADE"), nullable=True
    )
    rater_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    album: Mapped[Album | None] = relationship(  # noqa: F821
        back_populates="rates"
    )
    music: Mapped[Music | None] = relationship(  # noqa: F821
        back_populates="rates"
    )