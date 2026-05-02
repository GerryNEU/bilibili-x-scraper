from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from src.models import Post


logger = logging.getLogger(__name__)


async def main() -> None:
    from config import settings
    from src.bilibili import BilibiliCrawler
    from src.bilibili import CrawlerAuthError as BilibiliAuthError
    from src.bilibili import CrawlerFetchError as BilibiliFetchError
    from src.storage import StorageClient
    from src.transcriber import Transcriber
    from src.x import CrawlerAuthError as XCrawlerAuthError
    from src.x import CrawlerFetchError as XCrawlerFetchError
    from src.x import XCrawler

    logging.basicConfig(level=logging.INFO)

    app_settings = settings.Settings()
    storage = StorageClient(app_settings.DB_PATH)
    await storage.init_db()
    transcriber = Transcriber()

    for uid in app_settings.BILIBILI_UIDS:
        crawler = BilibiliCrawler(
            storage,
            app_settings.BILIBILI_SESSDATA,
            app_settings.BILIBILI_BUVID3,
            transcriber,
        )
        await _run_crawler(
            crawler.fetch_all_posts(uid),
            storage,
            "bilibili",
            uid,
            (BilibiliAuthError, BilibiliFetchError),
        )

    for username in app_settings.X_USERNAMES:
        crawler = XCrawler(
            storage,
            username,
            app_settings.X_USERNAME,
            app_settings.X_PASSWORD,
        )
        await _run_crawler(
            crawler.fetch_all_posts(username),
            storage,
            "x",
            username,
            (XCrawlerAuthError, XCrawlerFetchError),
        )


async def _run_crawler(
    posts: AsyncIterator[Post],
    storage: object,
    platform: str,
    author_id: str,
    crawler_errors: tuple[type[Exception], ...],
) -> None:
    try:
        async for post in posts:
            await storage.save_post(post)
            logger.info("Saved %s post %s for %s", platform, post.id, author_id)
            await asyncio.sleep(1.0)
    except crawler_errors as exc:
        logger.error("Skipping %s target %s: %s", platform, author_id, exc)


if __name__ == "__main__":
    asyncio.run(main())
