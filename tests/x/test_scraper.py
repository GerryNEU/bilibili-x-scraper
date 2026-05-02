import asyncio

import pytest

from src.x import scraper
from src.x.exceptions import CrawlerFetchError


class FakeResponse:
    def __init__(self, payload):
        self.url = "https://x.com/i/api/graphql/UserTweets"
        self._payload = payload

    async def json(self):
        return self._payload


class FakeMouse:
    async def wheel(self, x, y):
        return None


class FakePage:
    def __init__(self, payload=None, goto_error=None):
        self._payload = payload if payload is not None else {}
        self._goto_error = goto_error
        self._handlers = {}
        self.mouse = FakeMouse()
        self.closed = False

    def on(self, event, handler):
        self._handlers[event] = handler

    def set_default_timeout(self, timeout):
        self.timeout = timeout

    async def goto(self, url, wait_until, timeout):
        if self._goto_error is not None:
            raise self._goto_error

        handler = self._handlers.get("response")
        if handler is not None:
            handler(FakeResponse(self._payload))
            await asyncio.sleep(0)
            await asyncio.sleep(0)

    async def wait_for_load_state(self, state, timeout):
        return None

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self, page):
        self.page = page

    async def new_page(self):
        return self.page


def _tweet(post_id, text):
    return {
        "__typename": "Tweet",
        "rest_id": post_id,
        "legacy": {
            "full_text": text,
            "created_at": "Wed Oct 10 20:19:24 +0000 2018",
            "entities": {},
        },
    }


def _payload(*tweets):
    return {"data": {"tweets": list(tweets)}}


async def _without_retry(operation):
    return await operation()


@pytest.mark.asyncio
async def test_scrape_posts_yields_dicts(monkeypatch):
    monkeypatch.setattr(scraper, "_with_retry", _without_retry)
    monkeypatch.setattr(scraper, "MAX_IDLE_SCROLLS", 0)
    page = FakePage(_payload(_tweet("1", "first"), _tweet("2", "second")))

    posts = [
        post async for post in scraper.scrape_posts(FakeContext(page), "alice", None)
    ]

    assert [post["id"] for post in posts] == ["1", "2"]
    assert [post["text"] for post in posts] == ["first", "second"]
    assert posts[0]["url"] == "https://x.com/alice/status/1"


@pytest.mark.asyncio
async def test_scrape_posts_stops_on_last_post_id(monkeypatch):
    monkeypatch.setattr(scraper, "_with_retry", _without_retry)
    monkeypatch.setattr(scraper, "MAX_IDLE_SCROLLS", 0)
    page = FakePage(_payload(_tweet("1", "first"), _tweet("2", "second")))

    posts = [
        post async for post in scraper.scrape_posts(FakeContext(page), "alice", "2")
    ]

    assert [post["id"] for post in posts] == ["1"]


@pytest.mark.asyncio
async def test_scrape_posts_stops_on_empty_timeline(monkeypatch):
    monkeypatch.setattr(scraper, "_with_retry", _without_retry)
    monkeypatch.setattr(scraper, "MAX_IDLE_SCROLLS", 0)
    page = FakePage(_payload())

    posts = [
        post async for post in scraper.scrape_posts(FakeContext(page), "alice", None)
    ]

    assert posts == []


@pytest.mark.asyncio
async def test_scrape_posts_raises_crawler_fetch_error(monkeypatch):
    monkeypatch.setattr(scraper, "_with_retry", _without_retry)
    page = FakePage(goto_error=RuntimeError("navigation failed"))

    with pytest.raises(CrawlerFetchError):
        [
            post
            async for post in scraper.scrape_posts(FakeContext(page), "alice", None)
        ]

    assert page.closed is True
