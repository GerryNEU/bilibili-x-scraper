# Crawler Agent Lab

一个多平台内容爬虫，支持抓取 **Bilibili** 和 **X（Twitter）** 的帖子，存储到本地 SQLite 数据库，并使用设备端语音识别（Apple Silicon）转录 Bilibili 视频。

---

## 功能特性

- **Bilibili**：抓取任意用户的动态、视频和专栏文章
- **X**：通过 X 内部 GraphQL API 抓取任意用户的推文（无需付费 API 密钥）
- **断点续爬**：首次运行抓取完整历史记录，后续运行仅抓取新内容
- **视频转录**：使用 `mlx-whisper` 下载并转录 Bilibili 视频音频（Apple Silicon 上速度极快）
- **本地批量转录**：对本地已下载的整个视频文件夹进行批量转录
- **SQLite 存储**：所有帖子存储在本地，完整保留原始 JSON 数据

---

## 环境要求

- Python 3.12+
- [ffmpeg](https://ffmpeg.org/) — mlx-whisper 解码音频所需

  ```bash
  brew install ffmpeg
  ```

- Python 依赖：

  ```bash
  pip install -r requirements.txt
  ```

---

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone <repo-url>
cd crawler-agent-lab
pip install -r requirements.txt
```

### 2. 配置环境变量

将 `.env.example` 复制为 `.env` 并填入凭证：

```bash
cp .env.example .env
```

| 变量名 | 说明 |
|---|---|
| `BILIBILI_SESSDATA` | Bilibili `SESSDATA` Cookie |
| `BILIBILI_BUVID3` | Bilibili `buvid3` Cookie |
| `BILIBILI_BUVID4` | Bilibili `buvid4` Cookie（设备指纹，2024 年后必填）|
| `BILIBILI_BILI_JCT` | Bilibili `bili_jct` CSRF Cookie |
| `BILIBILI_DEDE_USER_ID` | Bilibili `DedeUserID` Cookie |
| `BILIBILI_DEDE_USER_ID_CKMD5` | Bilibili `DedeUserID__ckMd5` Cookie |
| `X_COOKIE_STRING` | X 完整 Cookie 字符串，必须包含 `ct0` 和 `auth_token` |
| `DB_PATH` | SQLite 数据库路径（默认：`data/posts.db`）|
| `BILIBILI_UIDS` | 逗号分隔的 Bilibili 用户 UID 列表 |
| `X_USERNAMES` | 逗号分隔的 X 用户名列表（`@` 前缀可选）|

**如何获取 Cookie：**

- **Bilibili**：登录 bilibili.com → 开发者工具 → Application → Cookies → 逐一复制上表中的值。
- **X**：登录 x.com → 开发者工具 → Network → 任意 `x.com` 请求 → Headers → 复制完整的 `Cookie:` 请求头内容。字符串中必须包含 `ct0=...` 和 `auth_token=...`。若值中包含特殊字符，请在 `.env` 中用双引号包裹：

  ```
  X_COOKIE_STRING="auth_token=abc123; ct0=xyz789; ..."
  ```

---

## 使用方式

### 运行全部爬虫（Bilibili + X）

```bash
python -m src.scheduler.main
```

### 仅运行 X 爬虫

```bash
python -m scripts.crawl_x
```

### 批量转录本地视频文件夹

```bash
python scripts/transcribe_local.py /path/to/videos
```

每个视频会在同目录生成同名 `.txt` 转录文件，已转录的文件自动跳过。

---

## 爬取行为说明

爬虫针对每个 `(平台, 用户, 内容类型)` 组合独立维护状态，分为两种模式：

| 运行阶段 | 行为 |
|---|---|
| 首次运行（`crawl_complete = 0`）| 抓取完整历史记录，跳过数据库中已存在的帖子 |
| 后续运行（`crawl_complete = 1`）| 仅抓取最近一条已保存帖子之后的新内容 |

首次完整爬取成功后自动设置 `crawl_complete = 1`。如需强制重新全量爬取，可直接修改 `cursors` 表：

```sql
UPDATE cursors SET crawl_complete = 0 WHERE platform = 'x' AND author_id = 'username';
```

---

## 项目结构

```
src/
  bilibili/       — Bilibili 爬虫（动态、视频、专栏）
  x/              — X 爬虫（基于 GraphQL，无需 API 密钥）
  transcriber/    — 音频下载 + mlx-whisper 转录
  storage/        — SQLite 客户端
  models/         — Pydantic Post 数据模型
  scheduler/      — 统一调度所有爬虫
config/
  settings.py     — 基于环境变量的配置管理
scripts/
  crawl_x.py              — 单独运行 X 爬虫
  transcribe_local.py     — 本地视频批量转录
```

---

## 技术说明

- **Bilibili**：使用 WBI 签名（`w_rid` + `wts`）对 API 请求进行认证，并携带全部六个必要的 Session Cookie，避免触发 412 反爬。翻页间隔随机为 3–7 秒。
- **X**：使用 X Web 端内置的公开 Bearer Token，配合用户自身的 Cookie 和 CSRF Token（`ct0`）调用 `x.com/i/api/graphql`，无需申请开发者账号。
- **转录**：使用 `mlx-whisper`，`language="zh"` 识别普通话。模型通过 MLX 运行在 Apple Neural Engine 上。默认使用 `whisper-base`，如需更高精度可在 `transcribe_local.py` 或 `Transcriber` 中修改 `MODEL_REPO` 为 `whisper-large-v3`。
