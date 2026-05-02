from __future__ import annotations

import re

import httpx

from src.x.exceptions import CrawlerAuthError


_BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def build_client(cookie_string: str) -> httpx.AsyncClient:
    ct0 = _extract_ct0(cookie_string)
    if not ct0:
        raise CrawlerAuthError("X cookie string is missing ct0 (CSRF token)")
    return httpx.AsyncClient(
        base_url="https://x.com",
        headers={
            "Authorization": f"Bearer {_BEARER_TOKEN}",
            "Cookie": cookie_string,
            "X-Csrf-Token": ct0,
            "User-Agent": _USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "X-Twitter-Active-User": "yes",
            "X-Twitter-Auth-Type": "OAuth2Session",
            "X-Twitter-Client-Language": "en",
        },
        timeout=30.0,
    )


def _extract_ct0(cookie_string: str) -> str | None:
    match = re.search(r"(?:^|;\s*)ct0=([^;]+)", cookie_string)
    return match.group(1).strip() if match else None
