from unittest.mock import AsyncMock

import httpx
import pytest

from src.bilibili.exceptions import CrawlerAuthError, CrawlerFetchError
from src.bilibili.fetcher import fetch_articles, fetch_dynamics, fetch_videos


def response(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(status_code, json=payload, request=httpx.Request("GET", "https://api.bilibili.com/test"))


async def collect(async_iterable):
    return [item async for item in async_iterable]


@pytest.mark.asyncio
async def test_fetch_dynamics_yields_items():
    items = [{"id_str": "1"}, {"id_str": "2"}]
    client = AsyncMock()
    client.get.return_value = response(200, {"code": 0, "data": {"items": items, "has_more": 0}})

    result = await collect(fetch_dynamics(client, "uid1", None))

    assert result == items


@pytest.mark.asyncio
async def test_fetch_dynamics_stops_on_last_post_id():
    items = [{"id_str": "1"}, {"id_str": "stop"}, {"id_str": "3"}]
    client = AsyncMock()
    client.get.return_value = response(200, {"code": 0, "data": {"items": items, "has_more": 0}})

    result = await collect(fetch_dynamics(client, "uid1", "stop"))

    assert result == [{"id_str": "1"}]


@pytest.mark.asyncio
async def test_fetch_dynamics_stops_on_empty_page():
    client = AsyncMock()
    client.get.return_value = response(200, {"code": 0, "data": {"items": [], "has_more": 0}})

    result = await collect(fetch_dynamics(client, "uid1", None))

    assert result == []


@pytest.mark.asyncio
async def test_fetch_videos_yields_items():
    items = [{"aid": 1, "bvid": "BV1"}]
    client = AsyncMock()
    client.get.side_effect = [
        response(200, {"code": 0, "data": {"list": {"vlist": items}}}),
        response(200, {"code": 0, "data": {"list": {"vlist": []}}}),
    ]

    result = await collect(fetch_videos(client, "uid1", None))

    assert result == items


@pytest.mark.asyncio
async def test_fetch_videos_stops_on_last_post_id():
    client = AsyncMock()
    client.get.return_value = response(200, {"code": 0, "data": {"list": {"vlist": [{"aid": 1}]}}})

    result = await collect(fetch_videos(client, "uid1", "1"))

    assert result == []


@pytest.mark.asyncio
async def test_fetch_articles_yields_items():
    items = [{"id": 1, "title": "Article"}]
    client = AsyncMock()
    client.get.side_effect = [
        response(200, {"code": 0, "data": {"articles": items}}),
        response(200, {"code": 0, "data": {"articles": []}}),
    ]

    result = await collect(fetch_articles(client, "uid1", None))

    assert result == items


@pytest.mark.asyncio
async def test_fetch_raises_crawler_fetch_error():
    client = AsyncMock()
    client.get.return_value = response(500, {"code": -1})

    with pytest.raises(CrawlerFetchError):
        await collect(fetch_dynamics(client, "uid1", None))


@pytest.mark.asyncio
async def test_fetch_raises_crawler_auth_error():
    client = AsyncMock()
    client.get.return_value = response(401, {"code": -101})

    with pytest.raises(CrawlerAuthError):
        await collect(fetch_dynamics(client, "uid1", None))
