from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import suppress
from typing import TYPE_CHECKING

from src.models import Post
from src.x import auth, parser, scraper

if TYPE_CHECKING:
    from src.storage import StorageClient


class XCrawler:
    def __init__(
        self,
        storage: "StorageClient",
        username: str,
        x_username: str,
        x_password: str,
    ) -> None:
        self.storage = storage
        self.username = username
        self.x_username = x_username
        self.x_password = x_password

    async def fetch_all_posts(self, username: str) -> AsyncIterator[Post]:
        complete = await self.storage.is_crawl_complete("x", username, "post")
        if complete:
            stop_at = await self.storage.get_last_post_id("x", username, "post")
        else:
            stop_at = None

        context = await auth.login(self.x_username, self.x_password)
        try:
            async for raw_post in scraper.scrape_posts(context, username, stop_at):
                post = parser.parse_post(raw_post, username)
                if post is None:
                    continue
                if not complete and await self.storage.post_exists("x", post.id):
                    continue
                yield post

            if not complete:
                await self.storage.mark_crawl_complete("x", username, "post")
        finally:
            await _close_context(context)


async def _close_context(context: object) -> None:
    with suppress(Exception):
        await context.close()

    browser = getattr(context, "_x_crawler_browser", None)
    if browser is not None:
        with suppress(Exception):
            await browser.close()

    playwright = getattr(context, "_x_crawler_playwright", None)
    if playwright is not None:
        with suppress(Exception):
            await playwright.stop()
