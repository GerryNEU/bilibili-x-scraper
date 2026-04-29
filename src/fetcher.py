from urllib.parse import urlparse

import httpx


def fetch(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")

    response = httpx.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.text
