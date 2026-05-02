import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import whisper
import yt_dlp

from src.transcriber.exceptions import TranscribeError


class Transcriber:
    def __init__(self, model_name: str = "base") -> None:
        self.model = whisper.load_model(model_name)

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

            try:
                result = await asyncio.to_thread(self.model.transcribe, str(audio_path))
            except Exception as exc:
                raise TranscribeError("Failed to transcribe audio") from exc

            return self._extract_text(result)
        finally:
            self._delete_temp_audio(audio_path)

    def _download_audio(self, video_url: str, audio_path: Path) -> None:
        options = {
            "format": "bestaudio/best",
            "outtmpl": str(audio_path),
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([video_url])

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
