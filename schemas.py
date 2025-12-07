# schemas.py
from pydantic import BaseModel
from datetime import datetime

class Series(BaseModel):
    id: str
    title: str
    cover_url: str
    created: datetime
    updated: datetime

    class Config:
        from_attributes = True

class Chapter(BaseModel):
    id: str
    chapter_number: float
    title: str | None = None
    series_id: str
    created: datetime

    class Config:
        from_attributes = True

class PagesResponse(BaseModel):
    pages: list[str]
    next_chapter: str | None
    prev_chapter: str | None