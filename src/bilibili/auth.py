import httpx


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def build_client(sessdata: str, buvid3: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.bilibili.com",
        cookies={
            "SESSDATA": sessdata,
            "buvid3": buvid3,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=15.0,
    )
