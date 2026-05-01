from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from src.transcriber import TranscribeError, Transcriber


async def run_sync_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


def build_transcriber(model):
    with patch("src.transcriber.transcriber.whisper.load_model", return_value=model):
        return Transcriber()


@contextmanager
def mocked_temp_file():
    with (
        patch("src.transcriber.transcriber.tempfile.mkstemp", return_value=(1, "/tmp/audio.mock")),
        patch("src.transcriber.transcriber.os.close"),
        patch("src.transcriber.transcriber.Path.unlink") as unlink_mock,
        patch("src.transcriber.transcriber.Path.glob", return_value=[]),
        patch("src.transcriber.transcriber.asyncio.to_thread", side_effect=run_sync_thread),
    ):
        yield unlink_mock


def patch_downloader(download_side_effect=None):
    downloader = Mock()
    downloader.download.side_effect = download_side_effect

    manager = Mock()
    manager.__enter__ = Mock(return_value=downloader)
    manager.__exit__ = Mock(return_value=None)

    return patch("src.transcriber.transcriber.yt_dlp.YoutubeDL", return_value=manager), downloader


@pytest.mark.asyncio
async def test_transcribe_returns_transcript():
    model = Mock()
    model.transcribe.return_value = {"text": "hello transcript"}
    transcriber = build_transcriber(model)
    downloader_patch, downloader = patch_downloader()

    with mocked_temp_file(), downloader_patch:
        result = await transcriber.transcribe("https://example.com/video")

    assert result == "hello transcript"
    downloader.download.assert_called_once_with(["https://example.com/video"])
    model.transcribe.assert_called_once_with("/tmp/audio.mock")


@pytest.mark.asyncio
async def test_transcribe_returns_empty_string_on_no_speech():
    model = Mock()
    model.transcribe.return_value = {"segments": []}
    transcriber = build_transcriber(model)
    downloader_patch, _ = patch_downloader()

    with mocked_temp_file(), downloader_patch:
        result = await transcriber.transcribe("https://example.com/video")

    assert result == ""


@pytest.mark.asyncio
async def test_transcribe_raises_on_download_failure():
    model = Mock()
    transcriber = build_transcriber(model)
    downloader_patch, _ = patch_downloader(RuntimeError("download failed"))

    with mocked_temp_file() as unlink_mock, downloader_patch:
        with pytest.raises(TranscribeError):
            await transcriber.transcribe("https://example.com/video")

    model.transcribe.assert_not_called()
    assert unlink_mock.called


@pytest.mark.asyncio
async def test_transcribe_raises_on_whisper_failure():
    model = Mock()
    model.transcribe.side_effect = RuntimeError("whisper failed")
    transcriber = build_transcriber(model)
    downloader_patch, _ = patch_downloader()

    with mocked_temp_file() as unlink_mock, downloader_patch:
        with pytest.raises(TranscribeError):
            await transcriber.transcribe("https://example.com/video")

    assert unlink_mock.called
