from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, Any, Iterator

from src.x.exceptions import CrawlerFetchError

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page, Response


PROFILE_TIMEOUT_MS = 30_000
POST_LOAD_TIMEOUT_SECONDS = 5
MAX_IDLE_SCROLLS = 2


async def scrape_posts(
    context: "BrowserContext", username: str, last_post_id: str | None
) -> AsyncIterator[dict]:
    page = await context.new_page()
    post_queue: asyncio.Queue[dict] = asyncio.Queue()
    seen_post_ids: set[str] = set()

    def response_handler(response: "Response") -> None:
        asyncio.create_task(_enqueue_posts(response, username, post_queue))

    page.on("response", response_handler)

    try:
        await _with_retry(lambda: _goto_profile(page, username))

        idle_scrolls = 0
        while True:
            yielded_post = False
            async for post in _drain_posts(post_queue):
                post_id = post["id"]
                if post_id == last_post_id:
                    return
                if post_id in seen_post_ids:
                    continue

                seen_post_ids.add(post_id)
                yielded_post = True
                yield post

            if idle_scrolls >= MAX_IDLE_SCROLLS:
                return

            before_count = len(seen_post_ids)
            await _with_retry(lambda: _scroll_for_more(page))

            try:
                post = await asyncio.wait_for(
                    post_queue.get(), timeout=POST_LOAD_TIMEOUT_SECONDS
                )
                await post_queue.put(post)
            except asyncio.TimeoutError:
                pass

            if len(seen_post_ids) == before_count and not yielded_post:
                idle_scrolls += 1
            else:
                idle_scrolls = 0
    except CrawlerFetchError:
        raise
    except Exception as exc:
        raise CrawlerFetchError("Failed to scrape X posts") from exc
    finally:
        await page.close()


async def _with_retry(operation: Callable[[], Awaitable[Any]]) -> Any:
    try:
        from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
    except ImportError as exc:
        raise CrawlerFetchError("tenacity is required for X scraping retries") from exc

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        ):
            with attempt:
                return await operation()
    except Exception as exc:
        raise CrawlerFetchError("X page operation failed") from exc


async def _goto_profile(page: "Page", username: str) -> None:
    page.set_default_timeout(PROFILE_TIMEOUT_MS)
    await page.goto(
        f"https://x.com/{username}",
        wait_until="domcontentloaded",
        timeout=PROFILE_TIMEOUT_MS,
    )


async def _scroll_for_more(page: "Page") -> None:
    await page.mouse.wheel(0, 2500)
    await page.wait_for_load_state("networkidle", timeout=PROFILE_TIMEOUT_MS)


async def _enqueue_posts(
    response: "Response", username: str, post_queue: asyncio.Queue[dict]
) -> None:
    if not _is_timeline_response(response.url):
        return

    try:
        payload = await response.json()
    except Exception:
        return

    for post in _extract_posts(payload, username):
        await post_queue.put(post)


def _is_timeline_response(url: str) -> bool:
    timeline_markers = (
        "UserTweets",
        "UserTweetsAndReplies",
        "HomeTimeline",
        "TweetDetail",
    )
    return any(marker in url for marker in timeline_markers)


async def _drain_posts(post_queue: asyncio.Queue[dict]) -> AsyncIterator[dict]:
    while not post_queue.empty():
        yield await post_queue.get()


def _extract_posts(payload: Any, username: str) -> list[dict]:
    posts: list[dict] = []
    for tweet in _walk_tweets(payload):
        post = _tweet_to_post(tweet, username)
        if post is not None:
            posts.append(post)
    return posts


def _walk_tweets(value: Any) -> Iterator[dict]:
    if isinstance(value, dict):
        tweet = _unwrap_tweet(value)
        if tweet is not None:
            yield tweet

        for child in value.values():
            yield from _walk_tweets(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_tweets(child)


def _unwrap_tweet(value: dict) -> dict | None:
    result = value.get("result") if "result" in value else value
    if not isinstance(result, dict):
        return None

    if result.get("__typename") == "Tweet" and isinstance(result.get("legacy"), dict):
        return result

    tweet_results = value.get("tweet_results")
    if isinstance(tweet_results, dict):
        nested_result = tweet_results.get("result")
        if (
            isinstance(nested_result, dict)
            and nested_result.get("__typename") == "Tweet"
            and isinstance(nested_result.get("legacy"), dict)
        ):
            return nested_result

    return None


def _tweet_to_post(tweet: dict, username: str) -> dict | None:
    legacy = tweet.get("legacy")
    if not isinstance(legacy, dict):
        return None

    post_id = tweet.get("rest_id") or legacy.get("id_str")
    text = _tweet_text(tweet, legacy)
    created_at = legacy.get("created_at")

    if not post_id or text is None or not created_at:
        return None

    return {
        "id": str(post_id),
        "text": text,
        "created_at": created_at,
        "media_urls": _media_urls(legacy),
        "url": f"https://x.com/{username}/status/{post_id}",
    }


def _tweet_text(tweet: dict, legacy: dict) -> str | None:
    note_tweet = tweet.get("note_tweet")
    if isinstance(note_tweet, dict):
        note_results = note_tweet.get("note_tweet_results")
        if isinstance(note_results, dict):
            note_result = note_results.get("result")
            if isinstance(note_result, dict) and isinstance(note_result.get("text"), str):
                return note_result["text"]

    full_text = legacy.get("full_text")
    if isinstance(full_text, str):
        return full_text

    text = legacy.get("text")
    return text if isinstance(text, str) else None


def _media_urls(legacy: dict) -> list[str]:
    urls: list[str] = []
    media_sources = []

    entities = legacy.get("entities")
    if isinstance(entities, dict):
        media_sources.extend(entities.get("media") or [])

    extended_entities = legacy.get("extended_entities")
    if isinstance(extended_entities, dict):
        media_sources.extend(extended_entities.get("media") or [])

    for media in media_sources:
        if not isinstance(media, dict):
            continue

        image_url = media.get("media_url_https") or media.get("media_url")
        if isinstance(image_url, str) and image_url not in urls:
            urls.append(image_url)

        video_info = media.get("video_info")
        if not isinstance(video_info, dict):
            continue

        for variant in video_info.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            video_url = variant.get("url")
            if isinstance(video_url, str) and video_url not in urls:
                urls.append(video_url)

    return urls
