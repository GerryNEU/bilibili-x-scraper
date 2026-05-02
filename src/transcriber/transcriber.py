import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import mlx_whisper
import yt_dlp

from src.transcriber.exceptions import TranscribeError


_MLX_MODEL_REPOS: dict[str, str] = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
}


class Transcriber:
    def __init__(self, model_name: str = "base", http_headers: dict[str, str] | None = None) -> None:
        self._model_repo = _MLX_MODEL_REPOS.get(model_name, f"mlx-community/whisper-{model_name}-mlx")
        self._http_headers = http_headers or {}

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
        if self._http_headers:
            options["http_headers"] = self._http_headers

        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([video_url])

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
        return str(text).strip()

    @staticmethod
    def _delete_temp_audio(audio_path: Path) -> None:
        try:
            audio_path.unlink(missing_ok=True)
            for path in audio_path.parent.glob(f"{audio_path.name}*"):
                path.unlink(missing_ok=True)
        except OSError:
            pass
