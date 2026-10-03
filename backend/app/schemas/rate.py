from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    album_id: int | None = None
    music_id: int | None = None
    rater_name: str
    rate: int
    description: str
    is_generated: bool


class RateSummary(BaseModel):
    count: int
    average: float | None = None


class RateCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rater_name: str = Field(min_length=1, max_length=255)
    rate: int = Field(ge=1, le=5)
    description: str = Field(min_length=1)


class RateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rater_name: str | None = Field(default=None, min_length=1, max_length=255)
    rate: int | None = Field(default=None, ge=1, le=5)
    description: str | None = Field(default=None, min_length=1)


class RateListOut(BaseModel):
    """Paginated rates plus high-level summary for the whole target."""

    items: list[RateOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    summary: RateSummary