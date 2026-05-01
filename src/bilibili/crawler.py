from collections.abc import AsyncIterator
import logging

from src.bilibili import auth
from src.bilibili.exceptions import CrawlerAuthError, CrawlerFetchError
from src.bilibili.fetcher import fetch_articles, fetch_dynamics, fetch_videos
from src.bilibili.parser import parse_article, parse_dynamic, parse_video
from src.models import Post
from src.storage import StorageClient
from src.transcriber import TranscribeError, Transcriber


logger = logging.getLogger(__name__)


class BilibiliCrawler:
    def __init__(
        self,
        storage: StorageClient,
        sessdata: str,
        buvid3: str,
        transcriber: Transcriber,
    ) -> None:
        self.storage = storage
        self.sessdata = sessdata
        self.buvid3 = buvid3
        self.transcriber = transcriber

    async def fetch_all_posts(self, uid: str) -> AsyncIterator[Post]:
        client = auth.build_client(self.sessdata, self.buvid3)
        try:
            dynamic_cursor = await self.storage.get_last_post_id("bilibili", uid, "dynamic")
            async for raw in fetch_dynamics(client, uid, dynamic_cursor):
                yield parse_dynamic(raw)

            video_cursor = await self.storage.get_last_post_id("bilibili", uid, "video")
            async for raw in fetch_videos(client, uid, video_cursor):
                video_url = f"https://www.bilibili.com/video/{raw['bvid']}"
                try:
                    transcript = await self.transcriber.transcribe(video_url)
                except TranscribeError:
                    logger.warning("Failed to transcribe Bilibili video %s", raw.get("bvid"))
                    transcript = ""
                yield parse_video(raw, transcript)

            article_cursor = await self.storage.get_last_post_id("bilibili", uid, "article")
            async for raw in fetch_articles(client, uid, article_cursor):
                yield parse_article(raw)
        except CrawlerAuthError:
            raise
        except CrawlerFetchError:
            raise
        finally:
            await client.aclose()
