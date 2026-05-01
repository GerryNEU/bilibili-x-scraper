from datetime import timezone
import json

from src.bilibili.parser import parse_article, parse_dynamic, parse_video


def dynamic_raw(include_text: bool = True) -> dict:
    desc = {"text": "dynamic content"} if include_text else None
    return {
        "id_str": "dynamic-1",
        "modules": {
            "module_author": {
                "mid": 123,
                "name": "Dynamic Author",
                "pub_ts": 1700000000,
            },
            "module_dynamic": {
                "desc": desc,
                "major": {
                    "draw": {
                        "items": [
                            {"src": "https://example.com/image-1.jpg"},
                            {"src": "https://example.com/image-2.jpg"},
                        ]
                    }
                },
            },
        },
    }


def video_raw() -> dict:
    return {
        "aid": 456,
        "bvid": "BV123",
        "author": {"mid": 123, "name": "Video Author"},
        "title": "Video Title",
        "created": 1700000000,
        "pic": "https://example.com/cover.jpg",
    }


def article_raw() -> dict:
    return {
        "id": 789,
        "author": {"mid": 123, "name": "Article Author"},
        "title": "Article Title",
        "summary": "Article summary",
        "publish_time": 1700000000,
        "image_urls": ["https://example.com/article.jpg"],
    }


def test_parse_dynamic_returns_post():
    post = parse_dynamic(dynamic_raw())

    assert post.platform == "bilibili"
    assert post.post_type == "dynamic"
    assert post.id == "dynamic-1"
    assert post.url == "https://t.bilibili.com/dynamic-1"


def test_parse_dynamic_empty_content():
    post = parse_dynamic(dynamic_raw(include_text=False))

    assert post.content == ""


def test_parse_video_uses_transcript():
    post = parse_video(video_raw(), "hello transcript")

    assert post.content == "hello transcript"


def test_parse_video_empty_transcript():
    post = parse_video(video_raw(), "")

    assert post.content == ""


def test_parse_article_returns_post():
    post = parse_article(article_raw())

    assert post.platform == "bilibili"
    assert post.post_type == "article"
    assert post.title == "Article Title"


def test_parse_raw_json_is_original():
    raw = dynamic_raw()

    post = parse_dynamic(raw)

    assert post.raw_json == json.dumps(raw)


def test_parse_created_at_is_utc_aware():
    post = parse_article(article_raw())

    assert post.created_at.tzinfo is not None
    assert post.created_at.utcoffset() == timezone.utc.utcoffset(post.created_at)
