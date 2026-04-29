# ARCHITECTURE.md

## Project Scale Assessment
Scale: Large
Reasoning:
- Estimated file count > 10 (crawler modules, transcriber, models, storage, config, tests, entry points)
- Module count = 6 (models, storage, transcriber, bilibili, x, scheduler)
- External service dependencies on two platforms (Bilibili, X) plus a speech-to-text service, all with authentication
- Estimated Builder task count > 15 total across modules
Mode: Full
Estimated Builder count: 2
Estimated total tasks: 20
Testing required: yes

---

## Project Overview
Crawl all posts (动态, 视频, 专栏) from specified Bilibili UP主 and all original posts from specified X users, transcribing Bilibili video audio to text, and storing everything in a structured, metadata-rich format optimized for future RAG pipeline ingestion.

## Tech Stack
- Language: Python 3.11+
- HTTP client: httpx (async)
- Browser automation: playwright (required for X; optional fallback for Bilibili)
- HTML parsing: BeautifulSoup4
- Transcription: OpenAI Whisper (local, via `openai-whisper` package)
- Database: SQLite via aiosqlite
- Data modeling: pydantic v2
- Testing: pytest + pytest-asyncio
- Other dependencies: python-dotenv (credential loading), tenacity (retry logic), yt-dlp (Bilibili video audio extraction)

## Directory Structure
```
src/
  ├── models/        Shared pydantic data models (Post, Author)
  ├── storage/       SQLite persistence — schema, write, dedup, query
  ├── transcriber/   Audio-to-text — download audio, run Whisper, return transcript
  ├── bilibili/      Bilibili crawler — auth, fetch 动态/视频/专栏, parse
  ├── x/             X crawler — auth, fetch original posts only, parse
  └── scheduler/     Orchestration, rate limiting, incremental resume, entry point
tests/
  ├── bilibili/      Unit tests for Bilibili fetch and parse logic
  ├── x/             Unit tests for X fetch and parse logic
  ├── transcriber/   Unit tests for transcriber (mock Whisper)
  └── storage/       Unit tests for Storage write/dedup/query logic
config/
  └── settings.py    Runtime config — credentials and targets loaded from env
.env.example         Template for required environment variables (never committed)
```

## Module Boundaries

### Module A — models
- Owns: `Post` and `Author` pydantic schemas; no I/O logic
- May access: nothing (leaf module, no dependencies)
- Must NOT access: storage, transcriber, bilibili, x, scheduler
- Exposes: `Post`, `Author` classes importable by all other modules

### Module B — storage
- Owns: SQLite schema definition, all DB read/write operations, deduplication, incremental cursor (last crawled post ID per platform/author)
- May access: `models`
- Must NOT access: `bilibili`, `x`, `transcriber`, `scheduler`
- Exposes: `StorageClient` — `save_post()`, `post_exists()`, `get_posts()`, `get_last_post_id()`

### Module C — transcriber
- Owns: downloading audio from a video URL, running speech-to-text, returning transcript text
- May access: nothing (leaf module; receives a URL string, returns a string)
- Must NOT access: `bilibili`, `x`, `storage`, `scheduler`
- Exposes: `Transcriber` — `transcribe(video_url: str) -> str`

### Module D — bilibili
- Owns: Bilibili authentication; fetching 动态, 视频, 专栏; parsing each post type; calling transcriber for 视频; incremental pagination using last post ID
- May access: `models`, `storage`, `transcriber`
- Must NOT access: `x`, `scheduler`
- Exposes: `BilibiliCrawler` — `fetch_all_posts(uid: str)`

### Module E — x
- Owns: X authentication via playwright; fetching original posts only (no retweets, no replies); parsing; incremental pagination using last post ID
- May access: `models`, `storage`
- Must NOT access: `bilibili`, `transcriber`, `scheduler`
- Exposes: `XCrawler` — `fetch_all_posts(username: str)`

### Module F — scheduler
- Owns: CLI entry point, task orchestration, rate-limit coordination, retry policy, incremental resume coordination
- May access: `bilibili`, `x`, `storage`, `models`
- Must NOT access: platform internals or `transcriber` directly (must call only public crawler interfaces)
- Exposes: `main()` — CLI entry point

## Data Flow
```
[config/env]
    │ credentials + target user IDs
    ▼
[scheduler]
    │
    ├──► [bilibili]
    │       ├── 动态 ──────────────────────────────────► parse ──► Post ──► [storage]
    │       ├── 专栏 ──────────────────────────────────► parse ──► Post ──► [storage]
    │       └── 视频 ──► [transcriber] ──► transcript ──► parse ──► Post ──► [storage]
    │                         │
    │                    (download audio via yt-dlp → Whisper → text)
    │
    └──► [x]
            └── original posts only ──► parse ──► Post ──► [storage] ──► SQLite
```

## Data Model (RAG-Optimized)
All posts are stored with the following fields to maximize future RAG usability:

| Field | Type | Notes |
|-------|------|-------|
| `id` | str | Platform-native post ID |
| `platform` | str | `"bilibili"` or `"x"` |
| `post_type` | str | `"dynamic"`, `"video"`, `"article"`, `"post"` |
| `author_id` | str | Platform UID / username |
| `author_name` | str | Display name |
| `content` | str | Clean plain text — for video: Whisper transcript; primary RAG input |
| `title` | str \| None | Present for 视频 and 专栏; null for 动态 and X posts |
| `url` | str | Canonical post URL |
| `created_at` | datetime | Post publish time (UTC) |
| `media_urls` | list[str] | Image URLs (JSON-serialized in SQLite); video URL stored here too |
| `raw_json` | str | Original platform response, for reprocessing |
| `crawled_at` | datetime | Crawl timestamp (UTC) |

## Incremental Crawl Design
- `storage` tracks the most recently crawled post ID per `(platform, author_id)` pair in a `cursors` table
- On each crawl run, crawlers fetch pages until they encounter a post ID that is already stored (or reach the cursor)
- New posts are saved; already-seen posts stop pagination
- This means posts are fetched newest-first from the platform, then stored; `content` ordering for RAG is handled by `created_at`

## Builder Assignment

### Estimated Builder count: 2
Reasoning:
- directories fully isolated: yes (`src/bilibili/` and `src/x/` share no files; `src/transcriber/` owned by Builder-A)
- interface stable early: yes (Storage and models interfaces defined before either crawler begins)
- parallel benefit > coordination cost: yes (crawlers are independent; both have 5+ tasks each)

| Builder | Owns | Working directory | Branch | Start when |
|---------|------|------------------|--------|------------|
| Builder-A | `models`, `storage`, `transcriber`, `bilibili`, `tests/bilibili`, `tests/transcriber`, `tests/storage` | `../proj-bilibili` | `feature/bilibili` | Project start |
| Builder-B | `x`, `scheduler`, `tests/x` | `../proj-x` | `feature/x` | After `StorageClient` and `Post` interfaces are stable (Builder-A defines them first) |

Builder-A must commit `src/models/` and `src/storage/` interfaces before Builder-B begins.

## Interface Contracts

### Contract 1 — Post (shared data model)
- Defined in: `src/models/post.py`
- Used by: all modules
- Schema:
  ```
  id:           str,      required
  platform:     str,      required — "bilibili" | "x"
  post_type:    str,      required — "dynamic" | "video" | "article" | "post"
  author_id:    str,      required
  author_name:  str,      required
  content:      str,      required — empty string allowed, never null; video: Whisper transcript
  title:        str,      optional — null if not applicable
  url:          str,      required
  created_at:   datetime, required — UTC
  media_urls:   list[str],required — empty list allowed
  raw_json:     str,      required — serialized original response
  crawled_at:   datetime, required — UTC, set by storage layer on save
  ```

### Contract 2 — StorageClient.save_post
- Caller: `bilibili.BilibiliCrawler`, `x.XCrawler`
- Provider: `storage.StorageClient`
- Input: `post: Post`
- Output: `None`
- Error handling: raises `StorageError` on DB failure
- Deduplication: silently skips if `(platform, id)` already exists — no exception raised

### Contract 3 — StorageClient.post_exists
- Caller: crawlers (pre-check before fetching detail)
- Provider: `storage.StorageClient`
- Input: `platform: str`, `post_id: str`
- Output: `bool`
- Error handling: raises `StorageError` on DB failure

### Contract 4 — StorageClient.get_posts
- Caller: `scheduler` (for reporting / future export)
- Provider: `storage.StorageClient`
- Input: `platform: str | None` (optional filter), `author_id: str | None` (optional filter), `limit: int = 100`, `offset: int = 0`
- Output: `list[Post]`
- Null / empty allowed: returns empty list if no results

### Contract 5 — StorageClient.get_last_post_id
- Caller: `bilibili.BilibiliCrawler`, `x.XCrawler`
- Provider: `storage.StorageClient`
- Input: `platform: str`, `author_id: str`
- Output: `str | None` — ID of the most recently crawled post; `None` if no prior crawl
- Error handling: raises `StorageError` on DB failure

### Contract 6 — BilibiliCrawler.fetch_all_posts
- Caller: `scheduler`
- Provider: `bilibili.BilibiliCrawler`
- Input: `uid: str` — Bilibili UP主 UID
- Output: `AsyncIterator[Post]` — yields new posts (newest-first); stops at already-seen post ID
- Error handling: raises `CrawlerAuthError` on auth failure; raises `CrawlerFetchError` on unrecoverable fetch failure; retries transient errors internally (max 3 attempts via tenacity)
- Null / empty allowed: yields nothing if no new posts since last crawl

### Contract 7 — XCrawler.fetch_all_posts
- Caller: `scheduler`
- Provider: `x.XCrawler`
- Input: `username: str` — X handle without `@`
- Output: `AsyncIterator[Post]` — yields new original posts only (newest-first); stops at already-seen post ID
- Error handling: raises `CrawlerAuthError` on auth failure; raises `CrawlerFetchError` on unrecoverable fetch failure; retries transient errors internally (max 3 attempts via tenacity)
- Null / empty allowed: yields nothing if no new posts since last crawl

### Contract 8 — Transcriber.transcribe
- Caller: `bilibili.BilibiliCrawler` (for 视频 post type only)
- Provider: `transcriber.Transcriber`
- Input: `video_url: str` — direct video or BV URL
- Output: `str` — transcript text; empty string if audio contains no speech
- Error handling: raises `TranscribeError` on download failure or Whisper failure
- Null / empty allowed: empty string returned if Whisper produces no output — never null

## Forbidden Behaviors
- `bilibili` must not write to SQLite directly — must call `StorageClient`
- `x` must not write to SQLite directly — must call `StorageClient`
- `scheduler` must not parse HTML, platform responses, or call `transcriber` directly
- `models` must not perform any I/O (no DB, no HTTP, no file access)
- `transcriber` must not know about Bilibili or X data structures — accepts a URL string, returns a string
- Credentials must never be hardcoded — loaded from environment variables only via `config/settings.py`
- `raw_json` must store the original response before any transformation — never store a re-serialized post
- X crawler must filter out retweets and replies — only original posts (no `RT @`, no posts starting with `@` in reply context)

## Open Questions
*(none — all resolved)*

## Resolved Decisions
- Bilibili post types: 动态, 视频, 专栏 (all three)
- X scope: original posts only — no retweets, no replies
- Crawl mode: incremental — first run fetches full history, subsequent runs fetch only posts newer than the last stored post ID
- Transcription: local Whisper (`openai-whisper`), language auto-detection enabled
- Credentials: `.env` file loaded via python-dotenv; `.env` is never committed

## Delivery Checklist

Architect Delivery Checklist:
- [x] All module boundaries clear with no overlapping responsibilities
- [x] Forbidden access rules defined for each module
- [x] Builder assignments follow directory boundaries
- [x] All cross-module interface contracts defined
- [x] Open questions listed
- [x] Testing required field set in Scale Assessment block: yes
