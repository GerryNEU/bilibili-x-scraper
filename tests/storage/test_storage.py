from datetime import datetime, timezone
import json

import pytest
import pytest_asyncio

from src.models import Post
from src.storage import StorageClient


@pytest_asyncio.fixture
async def client(tmp_path):
    storage = StorageClient(str(tmp_path / "test.db"))
    await storage.init_db()
    return storage


def make_post(
    post_id: str = "post-1",
    platform: str = "bilibili",
    post_type: str = "dynamic",
    author_id: str = "uid1",
    created_at: datetime | None = None,
    media_urls: list[str] | None = None,
) -> Post:
    created = created_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
    return Post(
        id=post_id,
        platform=platform,
        post_type=post_type,
        author_id=author_id,
        author_name=f"Author {author_id}",
        content=f"Content {post_id}",
        title=f"Title {post_id}",
        url=f"https://example.com/{post_id}",
        created_at=created,
        media_urls=media_urls or ["https://example.com/image.jpg"],
        raw_json=json.dumps({"id": post_id}),
        crawled_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_save_and_retrieve_post(client):
    post = make_post(media_urls=["https://example.com/1.jpg", "https://example.com/2.jpg"])

    await client.save_post(post)
    posts = await client.get_posts()

    assert len(posts) == 1
    saved = posts[0]
    assert saved.id == post.id
    assert saved.platform == post.platform
    assert saved.post_type == post.post_type
    assert saved.author_id == post.author_id
    assert saved.content == post.content
    assert saved.media_urls == post.media_urls
    assert saved.created_at == post.created_at


@pytest.mark.asyncio
async def test_save_post_dedup_silent(client):
    post = make_post()

    await client.save_post(post)
    await client.save_post(post)

    posts = await client.get_posts()
    assert len(posts) == 1


@pytest.mark.asyncio
async def test_post_exists_true(client):
    post = make_post()

    await client.save_post(post)

    assert await client.post_exists(post.platform, post.id) is True


@pytest.mark.asyncio
async def test_post_exists_false(client):
    assert await client.post_exists("bilibili", "missing") is False


@pytest.mark.asyncio
async def test_get_posts_filter_platform(client):
    bilibili_post = make_post(post_id="b1", platform="bilibili")
    x_post = make_post(post_id="x1", platform="x", post_type="post")

    await client.save_post(bilibili_post)
    await client.save_post(x_post)

    posts = await client.get_posts(platform="bilibili")
    assert [post.id for post in posts] == ["b1"]


@pytest.mark.asyncio
async def test_get_posts_filter_author_id(client):
    uid1_post = make_post(post_id="p1", author_id="uid1")
    uid2_post = make_post(post_id="p2", author_id="uid2")

    await client.save_post(uid1_post)
    await client.save_post(uid2_post)

    posts = await client.get_posts(author_id="uid1")
    assert [post.id for post in posts] == ["p1"]


@pytest.mark.asyncio
async def test_get_posts_empty(client):
    assert await client.get_posts() == []


@pytest.mark.asyncio
async def test_get_last_post_id_returns_id(client):
    post = make_post(post_id="dynamic-1", post_type="dynamic")

    await client.save_post(post)

    assert await client.get_last_post_id("bilibili", post.author_id, "dynamic") == "dynamic-1"


@pytest.mark.asyncio
async def test_get_last_post_id_returns_none(client):
    assert await client.get_last_post_id("bilibili", "uid1", "dynamic") is None


@pytest.mark.asyncio
async def test_cursor_scoped_by_post_type(client):
    dynamic = make_post(post_id="dynamic-1", post_type="dynamic")
    video = make_post(post_id="video-1", post_type="video")

    await client.save_post(dynamic)
    await client.save_post(video)

    assert await client.get_last_post_id("bilibili", "uid1", "dynamic") == "dynamic-1"
    assert await client.get_last_post_id("bilibili", "uid1", "video") == "video-1"


@pytest.mark.asyncio
async def test_cursor_not_regressed_on_duplicate(client):
    post = make_post(post_id="dynamic-1", post_type="dynamic")

    await client.save_post(post)
    await client.save_post(post)

    assert await client.get_last_post_id("bilibili", post.author_id, "dynamic") == "dynamic-1"
