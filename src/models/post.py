from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Post(BaseModel):
    id: str
    platform: Literal["bilibili", "x"]
    post_type: Literal["dynamic", "video", "article", "post"]
    author_id: str
    author_name: str
    content: str
    title: str | None = None
    url: str
    created_at: datetime
    media_urls: list[str] = Field(default_factory=list)
    raw_json: str
    crawled_at: datetime

    @field_validator("created_at", "crawled_at")
    @classmethod
    def require_timezone_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime fields must be timezone-aware UTC")
        return value.astimezone(timezone.utc)
