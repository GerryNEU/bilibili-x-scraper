import httpx


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def build_client(
    sessdata: str,
    buvid3: str,
    buvid4: str,
    bili_jct: str,
    dede_user_id: str,
    dede_user_id_ckmd5: str,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.bilibili.com",
        cookies={
            "SESSDATA": sessdata,
            "buvid3": buvid3,
            "buvid4": buvid4,
            "bili_jct": bili_jct,
            "DedeUserID": dede_user_id,
            "DedeUserID__ckMd5": dede_user_id_ckmd5,
        },
        headers={
            "User-Agent": USER_AGENT,
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        timeout=15.0,
    )
