from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RandomizeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    seed: int = -1
    album_rate_count: int = Field(
        default=2, alias="albumRateCount", ge=1, le=1000
    )
    music_rate_count: int = Field(
        default=2, alias="musicRateCount", ge=1, le=1000
    )


class RandomizeResponse(BaseModel):
    created_album_rates: int
    created_music_rates: int


class MessageResponse(BaseModel):
    message: str


class ResetRatesResponse(MessageResponse):
    deleted: int = 0