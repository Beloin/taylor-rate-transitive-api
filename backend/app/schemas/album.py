from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class AlbumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    name: str
    genre: str
    music_count: int
    release_date: date = Field(serialization_alias="releaseDate")
    llm_description: str
    llm_emotion_analysis: str
    llm_overall_public_reception: str