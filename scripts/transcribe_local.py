"""
Transcribe all video files in a local directory using mlx-whisper.

Saves each transcript as a .txt file beside the video.
Already-transcribed files (where .txt exists) are skipped.

Usage:
    python scripts/transcribe_local.py /path/to/videos
    python scripts/transcribe_local.py          # uses VIDEO_DIR constant below
"""

import argparse
import sys
from pathlib import Path

import mlx_whisper

VIDEO_DIR = "/Users/gerrysu/Documents/bilibili_download/video"
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".flv", ".webm", ".m4v", ".avi"}
MODEL_REPO = "mlx-community/whisper-base-mlx"


def transcribe_file(video_path: Path) -> None:
    txt_path = video_path.with_suffix(".txt")
    if txt_path.exists():
        print(f"[skip]  {video_path.name}")
        return

    print(f"[start] {video_path.name}")
    try:
        result = mlx_whisper.transcribe(
            str(video_path),
            path_or_hf_repo=MODEL_REPO,
            language="zh",
            verbose=False,
        )
        text = result.get("text", "").strip() if isinstance(result, dict) else ""
        txt_path.write_text(text, encoding="utf-8")
        print(f"[done]  {video_path.name}  ({len(text)} chars)")
    except Exception as exc:
        print(f"[error] {video_path.name}: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe local Bilibili videos")
    parser.add_argument("directory", nargs="?", default=VIDEO_DIR, help="Path to video directory")
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.is_dir():
        print(f"Error: {directory} is not a directory", file=sys.stderr)
        sys.exit(1)

    videos = sorted(p for p in directory.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)
    if not videos:
        print("No video files found.")
        return

    print(f"Found {len(videos)} video(s) in {directory}\n")
    for video in videos:
        transcribe_file(video)

    print("\nDone.")


if __name__ == "__main__":
    main()
