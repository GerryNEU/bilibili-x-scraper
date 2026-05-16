import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import mlx_whisper
import opencc
import yt_dlp

from src.transcriber.exceptions import TranscribeError


_TRADITIONAL_TO_SIMPLIFIED = opencc.OpenCC("t2s")


_MLX_MODEL_REPOS: dict[str, str] = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
}

# Domains the Bilibili cookies need to reach: the API host and the video CDN.
_COOKIE_DOMAINS: tuple[str, ...] = (".bilibili.com", ".bilivideo.com")
_COOKIE_EXPIRATION = "2147483647"


class Transcriber:
    def __init__(
        self,
        model_name: str = "base",
        cookies: dict[str, str] | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
    ) -> None:
        self._model_repo = _MLX_MODEL_REPOS.get(model_name, f"mlx-community/whisper-{model_name}-mlx")
        self._cookies = cookies or {}
        self._user_agent = user_agent
        self._referer = referer

    async def transcribe(self, video_url: str) -> str:
        fd, audio_file = tempfile.mkstemp(suffix=".audio")
        os.close(fd)
        audio_path = Path(audio_file)
        audio_path.unlink(missing_ok=True)

        try:
            try:
                await asyncio.to_thread(self._download_audio, video_url, audio_path)
            except Exception as exc:
                raise TranscribeError("Failed to download audio") from exc

            actual_path = self._find_downloaded_file(audio_path)

            try:
                result = await asyncio.to_thread(
                    mlx_whisper.transcribe,
                    str(actual_path),
                    path_or_hf_repo=self._model_repo,
                    language="zh",
                    verbose=False,
                )
            except Exception as exc:
                raise TranscribeError("Failed to transcribe audio") from exc

            return self._extract_text(result)
        finally:
            self._delete_temp_audio(audio_path)

    def _download_audio(self, video_url: str, audio_path: Path) -> None:
        options: dict[str, Any] = {
            "format": "worstaudio/bestaudio/best",
            "outtmpl": str(audio_path),
            "quiet": True,
            "no_warnings": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
        }

        http_headers: dict[str, str] = {}
        if self._user_agent:
            http_headers["User-Agent"] = self._user_agent
        if self._referer:
            http_headers["Referer"] = self._referer
        if http_headers:
            options["http_headers"] = http_headers

        cookie_file: Path | None = None
        if self._cookies:
            cookie_file = self._write_cookie_file()
            options["cookiefile"] = str(cookie_file)

        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([video_url])
        finally:
            if cookie_file is not None:
                cookie_file.unlink(missing_ok=True)

    def _write_cookie_file(self) -> Path:
        fd, path = tempfile.mkstemp(suffix=".cookies.txt")
        os.close(fd)
        lines = ["# Netscape HTTP Cookie File"]
        for domain in _COOKIE_DOMAINS:
            for name, value in self._cookies.items():
                lines.append("\t".join([domain, "TRUE", "/", "FALSE", _COOKIE_EXPIRATION, name, value]))
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return Path(path)

    @staticmethod
    def _find_downloaded_file(audio_path: Path) -> Path:
        # yt-dlp may append the real format extension (e.g. .audio → .audio.m4a)
        candidates = [p for p in audio_path.parent.glob(f"{audio_path.name}.*") if p.is_file()]
        return candidates[0] if candidates else audio_path

    @staticmethod
    def _extract_text(result: Any) -> str:
        if not isinstance(result, dict):
            return ""
        text = result.get("text")
        if text is None:
            return ""
        return _TRADITIONAL_TO_SIMPLIFIED.convert(str(text).strip())

    @staticmethod
    def _delete_temp_audio(audio_path: Path) -> None:
        try:
            audio_path.unlink(missing_ok=True)
            for path in audio_path.parent.glob(f"{audio_path.name}*"):
                path.unlink(missing_ok=True)
        except OSError:
            pass
