from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Series(BaseModel):
    id: str
    title: str
    cover_file_id: str
    description: Optional[str] = ""
    updated: str # Pocketbase returns string dates usually

class Chapter(BaseModel):
    id: str
    chapter_number: float
    title: Optional[str] = None
    series_id: str
    updated: str

class ChapterPages(BaseModel):
    pages: List[str] # List of File IDs
    next_chapter: Optional[str]
    prev_chapter: Optional[str]