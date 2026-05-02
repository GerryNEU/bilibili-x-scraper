"""Run only the X crawler. Usage: python scripts/crawl_x.py"""

import asyncio
import logging


logger = logging.getLogger(__name__)


async def main() -> None:
    from config import settings
    from src.storage import StorageClient
    from src.x import CrawlerAuthError, CrawlerFetchError, XCrawler

    logging.basicConfig(level=logging.INFO)

    storage = StorageClient(settings.DB_PATH)
    await storage.init_db()

    for username in settings.X_USERNAMES:
        crawler = XCrawler(
            storage,
            username,
            settings.X_COOKIE_STRING,
        )
        try:
            async for post in crawler.fetch_all_posts(username):
                await storage.save_post(post)
                logger.info("Saved x post %s for %s", post.id, username)
                await asyncio.sleep(0.5)
        except (CrawlerAuthError, CrawlerFetchError) as exc:
            logger.error("Skipping x target %s: %s", username, exc)


if __name__ == "__main__":
    asyncio.run(main())
