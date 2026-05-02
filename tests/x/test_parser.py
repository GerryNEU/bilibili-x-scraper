import json

from src.x.parser import parse_post


def _raw_post(**overrides):
    raw = {
        "id": "123",
        "text": "hello world",
        "created_at": "Wed Oct 10 20:19:24 +0000 2018",
        "media_urls": ["https://example.com/image.jpg"],
        "url": "https://x.com/alice/status/123",
    }
    raw.update(overrides)
    return raw


def test_parse_post_returns_post():
    post = parse_post(_raw_post(), "alice")

    assert post is not None
    assert post.platform == "x"
    assert post.post_type == "post"
    assert post.id == "123"
    assert post.url == "https://x.com/alice/status/123"


def test_parse_post_filters_retweet():
    assert parse_post(_raw_post(text="RT @foo bar"), "alice") is None


def test_parse_post_filters_reply():
    assert parse_post(_raw_post(text="@foo bar"), "alice") is None


def test_parse_post_content_never_none():
    raw = _raw_post()
    del raw["text"]

    post = parse_post(raw, "alice")

    assert post is not None
    assert post.content == ""


def test_parse_post_raw_json_is_original():
    raw = _raw_post()

    post = parse_post(raw, "alice")

    assert post is not None
    assert post.raw_json == json.dumps(raw)


def test_parse_post_created_at_utc_aware():
    post = parse_post(_raw_post(), "alice")

    assert post is not None
    assert post.created_at.tzinfo is not None
    assert post.created_at.utcoffset() is not None


def test_parse_post_title_is_none():
    post = parse_post(_raw_post(), "alice")

    assert post is not None
    assert post.title is None
