from datetime import datetime, timezone
import json
from typing import Any

from src.models import Post


def parse_dynamic(raw: dict) -> Post:
    modules = raw["modules"]
    author = modules["module_author"]
    dynamic = modules.get("module_dynamic", {})
    desc = dynamic.get("desc") or {}
    major = dynamic.get("major") or {}
    draw = major.get("draw") or {}
    draw_items = draw.get("items") or []

    return Post(
        id=raw["id_str"],
        platform="bilibili",
        post_type="dynamic",
        author_id=str(author["mid"]),
        author_name=author["name"],
        content=str(desc.get("text") or ""),
        title=None,
        url=f"https://t.bilibili.com/{raw['id_str']}",
        created_at=_utc_from_timestamp(author["pub_ts"]),
        media_urls=_dynamic_image_urls(draw_items),
        raw_json=json.dumps(raw),
        crawled_at=datetime.now(timezone.utc),
    )


def parse_video(raw: dict, transcript: str) -> Post:
    return Post(
        id=str(raw["aid"]),
        platform="bilibili",
        post_type="video",
        author_id=str(raw["mid"]),
        author_name=str(raw["author"]),
        content=str(transcript or ""),
        title=raw["title"],
        url=f"https://www.bilibili.com/video/{raw['bvid']}",
        created_at=_utc_from_timestamp(raw["created"]),
        media_urls=[raw["pic"]] if raw.get("pic") else [],
        raw_json=json.dumps(raw),
        crawled_at=datetime.now(timezone.utc),
    )


def parse_article(raw: dict) -> Post:
    return Post(
        id=str(raw["id"]),
        platform="bilibili",
        post_type="article",
        author_id=str(raw["author"]["mid"]),
        author_name=raw["author"]["name"],
        content=str(raw.get("summary", "")),
        title=raw["title"],
        url=f"https://www.bilibili.com/read/cv{raw['id']}",
        created_at=_utc_from_timestamp(raw["publish_time"]),
        media_urls=list(raw.get("image_urls", [])),
        raw_json=json.dumps(raw),
        crawled_at=datetime.now(timezone.utc),
    )


def _utc_from_timestamp(value: int | float | str) -> datetime:
    return datetime.fromtimestamp(int(value), tz=timezone.utc)


def _dynamic_image_urls(items: list[Any]) -> list[str]:
    urls: list[str] = []
    for item in items:
        if isinstance(item, dict) and item.get("src"):
            urls.append(item["src"])
    return urls
