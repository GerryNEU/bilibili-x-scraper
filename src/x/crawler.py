from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from src.models import Post
from src.x import auth, parser, scraper
from src.x.exceptions import CrawlerAuthError, CrawlerFetchError

if TYPE_CHECKING:
    from src.storage import StorageClient


class XCrawler:
    def __init__(
        self,
        storage: "StorageClient",
        username: str,
        cookie_string: str,
    ) -> None:
        self.storage = storage
        self.username = username
        self.cookie_string = cookie_string

    async def fetch_all_posts(self, username: str) -> AsyncIterator[Post]:
        complete = await self.storage.is_crawl_complete("x", username, "post")
        stop_at = await self.storage.get_last_post_id("x", username, "post") if complete else None

        client = auth.build_client(self.cookie_string)
        try:
            newest_post_id: str | None = None
            async for raw_post in scraper.scrape_posts(client, username, stop_at):
                post = parser.parse_post(raw_post, username)
                if post is None:
                    continue
                if newest_post_id is None:
                    newest_post_id = post.id
                if not complete and await self.storage.post_exists("x", post.id):
                    continue
                yield post

            if newest_post_id is not None or not complete:
                await self.storage.mark_crawl_complete("x", username, "post", newest_post_id)
        except CrawlerAuthError:
            raise
        except CrawlerFetchError:
            raise
        finally:
            await client.aclose()
