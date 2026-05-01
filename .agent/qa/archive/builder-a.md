# QA Archive — Builder-A

## Q1
Status: ✅ Answered
Session: 1
Task: Task 1 — Create src/models/ (Post + Author pydantic models) + update requirements.txt
Question:
`ARCHITECTURE.md` Contract 1 does not list `post_type`, but the Task 1 requirements say Post must include `post_type: Literal["dynamic", "video", "article", "post"]` and describe it as from Contract 1. Should I follow the task requirement and include `post_type`, or should Contract 1 be treated as authoritative and omit it?

Answer:
`post_type` IS listed in Contract 1 — it is the third field in ARCHITECTURE.md (line: `post_type: str, required — "dynamic" | "video" | "article" | "post"`). Include it in Post exactly as the task requires: `post_type: Literal["dynamic", "video", "article", "post"]`. The task instruction and Contract 1 agree — no conflict.

## Q2
Status: ✅ Answered
Session: 1
Task: Task 2 — Create src/storage/ (StorageClient — schema + 4 methods + StorageError)
Question:
Task 2 requires a `cursors` table and `StorageClient.get_last_post_id(self, platform: str, author_id: str) -> str | None`, but `ARCHITECTURE.md` only defines StorageClient interfaces for `save_post`, `post_exists`, and `get_posts`; there is no cursor or `get_last_post_id` contract in the architecture. Should I implement `cursors` and `get_last_post_id` exactly as Task 2 specifies, or should I omit them because they are not defined in `ARCHITECTURE.md`?

Answer:
`get_last_post_id` IS defined in ARCHITECTURE.md as Contract 5, and the `cursors` table is described in the Incremental Crawl Design section: "storage tracks the most recently crawled post ID per (platform, author_id) pair in a cursors table." Builder-A read only Contracts 2–4 and missed Contract 5. Implement both the `cursors` table and `get_last_post_id` exactly as Task 2 specifies — they are fully architecture-defined.

## Q4
Status: ✅ Answered
Session: 4
Task: Task 1 — tests/storage/ StorageClient unit tests
Question:
The task requires using StorageClient(":memory:") for all tests. The current StorageClient opens a new aiosqlite connection in each method, so SQLite creates a separate in-memory database per method call. After await client.init_db(), a following await client.get_posts() fails with "no such table: posts". Fixing this requires modifying src/storage/client.py, but Task 1 only allows tests/storage/__init__.py and tests/storage/test_storage.py.

Answer:
Change the test requirement — do NOT modify src/storage/client.py. Use pytest's built-in tmp_path fixture with a real file path instead: `StorageClient(str(tmp_path / "test.db"))`. This gives full per-test isolation (tmp_path is unique per test) without touching storage code. The ":memory:" requirement in the task instruction was incorrect given the connection-per-method design.

## Q3
Status: ✅ Answered
Session: 2
Task: Session 2 Task 1 — Create src/transcriber/ (Transcriber + TranscribeError)
Question:
ARCHITECTURE.md in this checkout defines Contracts 1-6 only; Contract 8 is not present. Please confirm the Transcriber interface and behavior for Contract 8, and confirm whether implementation should use the yt-dlp Python API or subprocess, since the task allows both approaches.

Answer:
Your ARCHITECTURE.md is outdated — the worktree is behind develop. Run `git fetch origin && git merge origin/develop` in your worktree before continuing. After the merge, Contract 8 will be present.

Contract 8 — Transcriber.transcribe (authoritative copy for reference):
- Caller: bilibili.BilibiliCrawler (for 视频 post type only)
- Provider: transcriber.Transcriber
- Input: video_url: str — direct video or BV URL
- Output: str — transcript text; empty string if audio contains no speech — never null
- Error handling: raises TranscribeError on download failure or Whisper failure

yt-dlp decision: use the yt-dlp Python API (not subprocess). Reason: better error handling via Python exceptions, more testable (mock the API directly in tests), already a listed dependency.
