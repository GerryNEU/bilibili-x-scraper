# Crawler Agent Lab

A multi-platform content crawler for **Bilibili** and **X (Twitter)** that stores posts in a local SQLite database and transcribes Bilibili videos using on-device speech recognition (Apple Silicon).

---

## Features

- **Bilibili**: crawls dynamics, videos, and articles for any user ID
- **X**: crawls posts for any username via X's internal GraphQL API (no paid API key required)
- **Resumable crawl**: first run collects full history; subsequent runs collect only new posts
- **Video transcription**: downloads and transcribes Bilibili video audio using `mlx-whisper` (fast on Apple Silicon)
- **Local batch transcription**: transcribe an entire folder of downloaded videos
- **SQLite storage**: all posts stored locally with full raw JSON preserved

---

## Requirements

- Python 3.12+
- [ffmpeg](https://ffmpeg.org/) — required by mlx-whisper for audio decoding

  ```bash
  brew install ffmpeg
  ```

- Python dependencies:

  ```bash
  pip install -r requirements.txt
  ```

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd crawler-agent-lab
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `BILIBILI_SESSDATA` | Bilibili `SESSDATA` cookie |
| `BILIBILI_BUVID3` | Bilibili `buvid3` cookie |
| `BILIBILI_BUVID4` | Bilibili `buvid4` cookie (device fingerprint, required since 2024) |
| `BILIBILI_BILI_JCT` | Bilibili `bili_jct` CSRF cookie |
| `BILIBILI_DEDE_USER_ID` | Bilibili `DedeUserID` cookie |
| `BILIBILI_DEDE_USER_ID_CKMD5` | Bilibili `DedeUserID__ckMd5` cookie |
| `X_COOKIE_STRING` | Full X cookie string — must include `ct0` and `auth_token` |
| `DB_PATH` | SQLite database path (default: `data/posts.db`) |
| `BILIBILI_UIDS` | Comma-separated Bilibili user IDs to crawl |
| `X_USERNAMES` | Comma-separated X usernames to crawl (`@` prefix optional) |

**How to get cookies:**

- **Bilibili**: Log in at bilibili.com → DevTools → Application → Cookies → copy each value listed above.
- **X**: Log in at x.com → DevTools → Network → any `x.com` request → Headers → copy the full `Cookie:` header value. The string must contain `ct0=...` and `auth_token=...`. Wrap the value in double quotes in `.env` if it contains special characters.

  ```
  X_COOKIE_STRING="auth_token=abc123; ct0=xyz789; ..."
  ```

---

## Usage

### Run all crawlers (Bilibili + X)

```bash
python -m src.scheduler.main
```

### Run only the X crawler

```bash
python -m scripts.crawl_x
```

### Transcribe a folder of local videos

```bash
python scripts/transcribe_local.py /path/to/videos
```

Each video gets a `.txt` transcript file saved alongside it. Already-transcribed files are skipped automatically.

---

## Crawl behavior

The crawler operates in two modes, determined per `(platform, author, post_type)`:

| Run | Behavior |
|---|---|
| First run (`crawl_complete = 0`) | Fetches full post history, skipping duplicates already in the DB |
| Subsequent runs (`crawl_complete = 1`) | Fetches only posts newer than the most recent saved post |

The `crawl_complete` flag is set after a successful full crawl. To force a full re-crawl, reset the flag directly in the `cursors` table:

```sql
UPDATE cursors SET crawl_complete = 0 WHERE platform = 'x' AND author_id = 'username';
```

---

## Project structure

```
src/
  bilibili/       — Bilibili crawler (dynamics, videos, articles)
  x/              — X crawler (GraphQL-based, no API key needed)
  transcriber/    — Audio download + mlx-whisper transcription
  storage/        — SQLite client
  models/         — Pydantic Post model
  scheduler/      — Orchestrates all crawlers in sequence
config/
  settings.py     — Environment-based configuration
scripts/
  crawl_x.py              — Standalone X crawler script
  transcribe_local.py     — Batch transcription of local video files
```

---

## Technical notes

- **Bilibili**: uses WBI signing (`w_rid` + `wts`) to authenticate API requests and sends all six required session cookies to avoid 412 anti-bot responses. Inter-page delay is randomized between 3–7 seconds.
- **X**: calls `x.com/i/api/graphql` with the public web app bearer token plus the user's own cookies and CSRF token (`ct0`). No developer API account is needed.
- **Transcription**: uses `mlx-whisper` with `language="zh"` (Mandarin). The model runs on the Apple Neural Engine via MLX. Default model is `whisper-base`; edit `MODEL_REPO` in `transcribe_local.py` or `Transcriber` for higher accuracy (`whisper-large-v3`).
