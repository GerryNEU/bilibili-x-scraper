from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from src.models import Post


def parse_post(raw: dict, username: str) -> Post | None:
    raw_json = json.dumps(raw)
    text = raw.get("text") or ""

    if text.startswith("RT @") or text.startswith("@"):
        return None

    return Post(
        id=str(raw["id"]),
        platform="x",
        post_type="post",
        author_id=username,
        author_name=str(raw.get("author_name") or username),
        content=text,
        title=None,
        url=str(raw["url"]),
        created_at=_parse_created_at(raw["created_at"]),
        media_urls=_media_urls(raw.get("media_urls")),
        raw_json=raw_json,
        crawled_at=datetime.now(timezone.utc),
    )


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = parsedate_to_datetime(value)
    else:
        raise ValueError("created_at must be a datetime or string")

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _media_urls(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
