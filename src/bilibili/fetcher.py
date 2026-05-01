from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.bilibili.exceptions import CrawlerAuthError, CrawlerFetchError


class _TransientFetchError(Exception):
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(_TransientFetchError),
    reraise=True,
)
async def _request_json(client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = await client.get(path, params=params)
    except httpx.HTTPError as exc:
        raise _TransientFetchError("Failed to fetch Bilibili API") from exc

    if response.status_code in {401, 412}:
        raise CrawlerAuthError("Bilibili session cookies are invalid or expired")
    if response.status_code == 429 or response.status_code >= 500:
        raise _TransientFetchError("Bilibili API returned a transient HTTP error")

    try:
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CrawlerFetchError("Failed to fetch Bilibili API") from exc

    if not isinstance(payload, dict):
        raise CrawlerFetchError("Bilibili API response is malformed")

    code = payload.get("code")
    if code not in (None, 0):
        raise CrawlerFetchError("Bilibili API returned an error")

    return payload


async def _get_json(client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        return await _request_json(client, path, params)
    except _TransientFetchError as exc:
        raise CrawlerFetchError("Failed to fetch Bilibili API") from exc


def _require_dict(value: Any, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CrawlerFetchError(message)
    return value


def _require_list(value: Any, message: str) -> list[Any]:
    if not isinstance(value, list):
        raise CrawlerFetchError(message)
    return value


async def fetch_dynamics(
    client: httpx.AsyncClient,
    uid: str,
    last_post_id: str | None,
) -> AsyncIterator[dict]:
    offset = ""

    while True:
        payload = await _get_json(
            client,
            "/x/polymer/web-dynamic/v1/feed/space",
            {"host_mid": uid, "offset": offset},
        )
        data = _require_dict(payload.get("data"), "Dynamic response is missing data")
        items = _require_list(data.get("items"), "Dynamic response is missing items")

        if not items:
            return

        for item in items:
            if not isinstance(item, dict) or "id_str" not in item:
                raise CrawlerFetchError("Dynamic item is malformed")
            if item["id_str"] == last_post_id:
                return
            yield item

        if data.get("has_more") == 0:
            return
        offset = data.get("offset")
        if not offset:
            return


async def fetch_videos(
    client: httpx.AsyncClient,
    uid: str,
    last_post_id: str | None,
) -> AsyncIterator[dict]:
    page = 1

    while True:
        payload = await _get_json(
            client,
            "/x/space/wbi/arc/search",
            {"mid": uid, "pn": page, "ps": 30, "order": "pubdate"},
        )
        data = _require_dict(payload.get("data"), "Video response is missing data")
        list_data = _require_dict(data.get("list"), "Video response is missing list")
        items = _require_list(list_data.get("vlist"), "Video response is missing vlist")

        if not items:
            return

        for item in items:
            if not isinstance(item, dict) or "aid" not in item:
                raise CrawlerFetchError("Video item is malformed")
            if str(item["aid"]) == last_post_id:
                return
            yield item

        page += 1


async def fetch_articles(
    client: httpx.AsyncClient,
    uid: str,
    last_post_id: str | None,
) -> AsyncIterator[dict]:
    page = 1

    while True:
        payload = await _get_json(
            client,
            "/x/space/article",
            {"mid": uid, "pn": page, "ps": 30, "sort": "publish_time"},
        )
        data = _require_dict(payload.get("data"), "Article response is missing data")
        items = data.get("articles")
        if items is None:
            return
        items = _require_list(items, "Article response articles is malformed")

        if not items:
            return

        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                raise CrawlerFetchError("Article item is malformed")
            if str(item["id"]) == last_post_id:
                return
            yield item

        page += 1
