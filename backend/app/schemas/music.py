from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MusicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    album_id: int
    name: str
    genre: str
    llm_description: str
    llm_emotion_analysis: str | None = None