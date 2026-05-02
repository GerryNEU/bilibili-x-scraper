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
            for post_type, fetch_fn, parse_fn in [
                ("dynamic", fetch_dynamics, parse_dynamic),
                ("video", fetch_videos, None),
                ("article", fetch_articles, parse_article),
            ]:
                complete = await self.storage.is_crawl_complete("bilibili", uid, post_type)
                if complete:
                    cursor_id = await self.storage.get_last_post_id("bilibili", uid, post_type)
                    stop_at = cursor_id
                else:
                    stop_at = None

                if post_type == "video":
                    async for raw in fetch_videos(client, uid, stop_at):
                        post_id = str(raw["aid"])
                        if not complete and await self.storage.post_exists("bilibili", post_id):
                            continue
                        video_url = f"https://www.bilibili.com/video/{raw['bvid']}"
                        try:
                            transcript = await self.transcriber.transcribe(video_url)
                        except TranscribeError:
                            logger.warning("Failed to transcribe Bilibili video %s", raw.get("bvid"))
                            transcript = ""
                        yield parse_video(raw, transcript)
                else:
                    async for raw in fetch_fn(client, uid, stop_at):
                        if post_type == "dynamic":
                            post_id = raw["id_str"]
                        else:
                            post_id = str(raw["id"])
                        if not complete and await self.storage.post_exists("bilibili", post_id):
                            continue
                        yield parse_fn(raw)

                if not complete:
                    await self.storage.mark_crawl_complete("bilibili", uid, post_type)
        except CrawlerAuthError:
            raise
        except CrawlerFetchError:
            raise
        finally:
            await client.aclose()
