# ARCHITECTURE.md

## Project Scale Assessment
Scale: Large
Reasoning:
- Estimated file count > 10 (crawler modules, models, storage, config, tests, entry points)
- Module count = 4 (models, storage, bilibili, x, scheduler)
- External service dependencies on two platforms (Bilibili, X) with authentication required
- Estimated Builder task count > 10 total across modules
Mode: Full
Estimated Builder count: 2
Estimated total tasks: 16
Testing required: yes

---

## Project Overview
Crawl all posts from specified Bilibili UP主 and X users, storing them in a structured, metadata-rich format optimized for future RAG pipeline ingestion.

## Tech Stack
- Language: Python 3.11+
- HTTP client: httpx (async)
- Browser automation: playwright (required for X; optional fallback for Bilibili)
- HTML parsing: BeautifulSoup4
- Database: SQLite via aiosqlite
- Data modeling: pydantic v2
- Testing: pytest + pytest-asyncio
- Other dependencies: python-dotenv (credential loading), tenacity (retry logic)

## Directory Structure
```
src/
  ├── models/        Shared pydantic data models (Post, Author)
  ├── storage/       SQLite persistence — schema, write, dedup, query
  ├── bilibili/      Bilibili crawler — auth, fetch, parse
  ├── x/             X crawler — auth, fetch, parse
  └── scheduler/     Orchestration, rate limiting, entry point
tests/
  ├── bilibili/      Unit tests for Bilibili fetch and parse logic
  ├── x/             Unit tests for X fetch and parse logic
  └── storage/       Unit tests for Storage write/dedup/query logic
config/
  └── settings.py    Runtime config — credentials and targets loaded from env
.env.example         Template for required environment variables (never committed)
```

## Module Boundaries

### Module A — models
- Owns: `Post` and `Author` pydantic schemas; no I/O logic
- May access: nothing (leaf module, no dependencies)
- Must NOT access: storage, bilibili, x, scheduler
- Exposes: `Post`, `Author` classes importable by all other modules

### Module B — storage
- Owns: SQLite schema definition, all DB read/write operations, deduplication logic
- May access: `models`
- Must NOT access: `bilibili`, `x`, `scheduler`
- Exposes: `StorageClient` — `save_post()`, `post_exists()`, `get_posts()`

### Module C — bilibili
- Owns: Bilibili authentication, API/page fetch, response parsing, pagination
- May access: `models`, `storage`
- Must NOT access: `x`, `scheduler`
- Exposes: `BilibiliCrawler` — `fetch_all_posts(uid: str)`

### Module D — x
- Owns: X authentication via playwright, timeline fetch, response parsing, pagination
- May access: `models`, `storage`
- Must NOT access: `bilibili`, `scheduler`
- Exposes: `XCrawler` — `fetch_all_posts(username: str)`

### Module E — scheduler
- Owns: CLI entry point, task orchestration, rate-limit coordination, retry policy
- May access: `bilibili`, `x`, `storage`, `models`
- Must NOT access: platform internals (must call only public crawler interfaces)
- Exposes: `main()` — CLI entry point

## Data Flow
```
[config/env]
    │ credentials + target user IDs
    ▼
[scheduler]
    ├──► [bilibili] ──► fetch pages / API ──► parse ──► Post ──► [storage] ──► SQLite
    └──► [x]        ──► playwright browser ──► parse ──► Post ──► [storage] ──► SQLite
```

## Data Model (RAG-Optimized)
All posts are stored with the following fields to maximize future RAG usability:

| Field | Type | Notes |
|-------|------|-------|
| `id` | str | Platform-native post ID |
| `platform` | str | `"bilibili"` or `"x"` |
| `author_id` | str | Platform UID / username |
| `author_name` | str | Display name |
| `content` | str | Clean plain text — primary RAG input |
| `title` | str \| None | Present for Bilibili 专栏/视频; null for X |
| `url` | str | Canonical post URL |
| `created_at` | datetime | Post publish time (UTC) |
| `media_urls` | list[str] | Image/video URLs (JSON-serialized in SQLite) |
| `raw_json` | str | Original platform response, for reprocessing |
| `crawled_at` | datetime | Crawl timestamp (UTC) |

## Builder Assignment

### Estimated Builder count: 2
Reasoning:
- directories fully isolated: yes (`src/bilibili/` and `src/x/` share no files)
- interface stable early: yes (Storage and models interfaces defined before either crawler begins)
- parallel benefit > coordination cost: yes (crawlers are independent; both have 4+ tasks each)

| Builder | Owns | Working directory | Branch | Start when |
|---------|------|------------------|--------|------------|
| Builder-A | `models`, `storage`, `bilibili`, `tests/bilibili`, `tests/storage` | `../proj-bilibili` | `feature/bilibili` | Project start |
| Builder-B | `x`, `tests/x` | `../proj-x` | `feature/x` | After `StorageClient` interface is stable (Builder-A defines it first) |

Builder-A is responsible for defining and committing the `StorageClient` interface before Builder-B begins writing the X crawler.

## Interface Contracts

### Contract 1 — Post (shared data model)
- Defined in: `src/models/post.py`
- Used by: all modules
- Schema:
  ```
  id:           str,      required
  platform:     str,      required — "bilibili" | "x"
  author_id:    str,      required
  author_name:  str,      required
  content:      str,      required — empty string allowed, never null
  title:        str,      optional — null if not applicable
  url:          str,      required
  created_at:   datetime, required — UTC
  media_urls:   list[str],required — empty list allowed
  raw_json:     str,      required — serialized original response
  crawled_at:   datetime, required — UTC, set by storage layer
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

### Contract 5 — BilibiliCrawler.fetch_all_posts
- Caller: `scheduler`
- Provider: `bilibili.BilibiliCrawler`
- Input: `uid: str` — Bilibili UP主 UID
- Output: `AsyncIterator[Post]` — yields posts oldest-first
- Error handling: raises `CrawlerAuthError` on auth failure; raises `CrawlerFetchError` on unrecoverable fetch failure; retries transient errors internally (max 3 attempts via tenacity)
- Null / empty allowed: yields nothing if user has no posts

### Contract 6 — XCrawler.fetch_all_posts
- Caller: `scheduler`
- Provider: `x.XCrawler`
- Input: `username: str` — X handle without `@`
- Output: `AsyncIterator[Post]` — yields posts oldest-first
- Error handling: raises `CrawlerAuthError` on auth failure; raises `CrawlerFetchError` on unrecoverable fetch failure; retries transient errors internally (max 3 attempts via tenacity)
- Null / empty allowed: yields nothing if user has no posts

## Forbidden Behaviors
- `bilibili` must not write to SQLite directly — must call `StorageClient`
- `x` must not write to SQLite directly — must call `StorageClient`
- `scheduler` must not parse HTML or platform responses — must call crawler interfaces only
- `models` must not perform any I/O (no DB, no HTTP, no file access)
- Credentials must never be hardcoded — loaded from environment variables only via `config/settings.py`
- `raw_json` must store the original response before any transformation — never store a re-serialized post

## Open Questions
- Bilibili: target post types — 动态 (dynamic posts) only, or also 视频 (videos) and 专栏 (articles)? All three have different API endpoints.
- X: does "posts" include reposts (retweets) and replies, or original posts only?
- Should the crawler resume from the last crawled post (incremental) or always re-crawl all (full scan with dedup)?
- Rate limiting: should the scheduler enforce a global delay, or is per-platform independent throttling sufficient?
- Credentials delivery: will credentials be provided as `.env` file, OS keychain, or another mechanism?

## Delivery Checklist

Architect Delivery Checklist:
- [x] All module boundaries clear with no overlapping responsibilities
- [x] Forbidden access rules defined for each module
- [x] Builder assignments follow directory boundaries
- [x] All cross-module interface contracts defined
- [x] Open questions listed
- [x] Testing required field set in Scale Assessment block: yes
