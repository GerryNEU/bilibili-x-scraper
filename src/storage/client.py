from datetime import datetime, timezone
import json

import aiosqlite

from src.models import Post
from src.storage.exceptions import StorageError


class StorageClient:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._initialized = False

    async def init_db(self) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS posts (
                        id TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        post_type TEXT NOT NULL,
                        author_id TEXT NOT NULL,
                        author_name TEXT NOT NULL,
                        content TEXT NOT NULL,
                        title TEXT,
                        url TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        media_urls TEXT NOT NULL,
                        raw_json TEXT NOT NULL,
                        crawled_at TEXT NOT NULL,
                        PRIMARY KEY (platform, id)
                    )
                    """
                )
                await db.execute(
                    "DROP TABLE IF EXISTS cursors"
                )
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cursors (
                        platform TEXT NOT NULL,
                        author_id TEXT NOT NULL,
                        post_type TEXT NOT NULL,
                        last_post_id TEXT NOT NULL,
                        PRIMARY KEY (platform, author_id, post_type)
                    )
                    """
                )
                await db.commit()
            self._initialized = True
        except aiosqlite.Error as exc:
            raise StorageError("Failed to initialize database") from exc

    async def save_post(self, post: Post) -> None:
        self._require_initialized()
        crawled_at = datetime.now(timezone.utc)
        post_to_save = post.model_copy(update={"crawled_at": crawled_at})

        try:
            async with aiosqlite.connect(self.db_path) as db:
                result = await db.execute(
                    """
                    INSERT OR IGNORE INTO posts (
                        id,
                        platform,
                        post_type,
                        author_id,
                        author_name,
                        content,
                        title,
                        url,
                        created_at,
                        media_urls,
                        raw_json,
                        crawled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_to_save.id,
                        post_to_save.platform,
                        post_to_save.post_type,
                        post_to_save.author_id,
                        post_to_save.author_name,
                        post_to_save.content,
                        post_to_save.title,
                        post_to_save.url,
                        post_to_save.created_at.isoformat(),
                        json.dumps(post_to_save.media_urls),
                        post_to_save.raw_json,
                        post_to_save.crawled_at.isoformat(),
                    ),
                )
                if result.rowcount > 0:
                    await db.execute(
                        """
                        INSERT INTO cursors (platform, author_id, post_type, last_post_id)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(platform, author_id, post_type)
                        DO UPDATE SET last_post_id = excluded.last_post_id
                        """,
                        (
                            post_to_save.platform,
                            post_to_save.author_id,
                            post_to_save.post_type,
                            post_to_save.id,
                        ),
                    )
                await db.commit()
        except aiosqlite.Error as exc:
            raise StorageError("Failed to save post") from exc

    async def post_exists(self, platform: str, post_id: str) -> bool:
        self._require_initialized()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM posts WHERE platform = ? AND id = ? LIMIT 1",
                    (platform, post_id),
                ) as cursor:
                    row = await cursor.fetchone()
            return row is not None
        except aiosqlite.Error as exc:
            raise StorageError("Failed to check post existence") from exc

    async def get_posts(
        self,
        platform: str | None = None,
        author_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Post]:
        self._require_initialized()
        conditions: list[str] = []
        params: list[str | int] = []

        if platform is not None:
            conditions.append("platform = ?")
            params.append(platform)
        if author_id is not None:
            conditions.append("author_id = ?")
            params.append(author_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    f"""
                    SELECT
                        id,
                        platform,
                        post_type,
                        author_id,
                        author_name,
                        content,
                        title,
                        url,
                        created_at,
                        media_urls,
                        raw_json,
                        crawled_at
                    FROM posts
                    {where_clause}
                    ORDER BY created_at ASC
                    LIMIT ? OFFSET ?
                    """,
                    params,
                ) as cursor:
                    rows = await cursor.fetchall()
            return [self._row_to_post(row) for row in rows]
        except (aiosqlite.Error, ValueError, json.JSONDecodeError) as exc:
            raise StorageError("Failed to retrieve posts") from exc

    async def get_last_post_id(
        self,
        platform: str,
        author_id: str,
        post_type: str,
    ) -> str | None:
        self._require_initialized()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT last_post_id
                    FROM cursors
                    WHERE platform = ? AND author_id = ? AND post_type = ?
                    LIMIT 1
                    """,
                    (platform, author_id, post_type),
                ) as cursor:
                    row = await cursor.fetchone()
            return row[0] if row is not None else None
        except aiosqlite.Error as exc:
            raise StorageError("Failed to retrieve last post ID") from exc

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise StorageError("Database is not initialized; call init_db() first")

    def _row_to_post(self, row: aiosqlite.Row) -> Post:
        return Post(
            id=row["id"],
            platform=row["platform"],
            post_type=row["post_type"],
            author_id=row["author_id"],
            author_name=row["author_name"],
            content=row["content"],
            title=row["title"],
            url=row["url"],
            created_at=self._parse_datetime(row["created_at"]),
            media_urls=json.loads(row["media_urls"]),
            raw_json=row["raw_json"],
            crawled_at=self._parse_datetime(row["crawled_at"]),
        )

    def _parse_datetime(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
