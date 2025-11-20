from __future__ import annotations

"""
Transcript discovery and download using `yt_dlp`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import tempfile

import yt_dlp

from .config import Settings
from . import db
from .youtube_client import ChannelVideo


@dataclass
class TranscriptResult:
    text: Optional[str]
    language: Optional[str]
    is_auto_generated: bool


def _parse_vtt_to_text(vtt_path: Path) -> str:
    """
    Very small VTT -> plain text converter: drops timestamps and headers.
    """
    lines: list[str] = []
    for raw_line in vtt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("WEBVTT"):
            continue
        if "-->" in line:
            # timestamp line
            continue
        # cue index (e.g. "1", "2") – drop if it is just a number
        if line.isdigit():
            continue
        lines.append(line)
    return "\n".join(lines)


def fetch_transcript_for_video(url: str) -> TranscriptResult:
    """
    Attempt to download subtitles for a single video as text.

    Preference order:
      1. Manually provided subtitles in English.
      2. Automatically generated subtitles in English.

    If nothing can be downloaded, returns TranscriptResult with text=None.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # First try manual subtitles.
        base_opts = {
            "skip_download": True,
            "quiet": True,
            "writesubtitles": True,
            "writeautomaticsub": False,
            "subtitlesformat": "vtt",
            "subtitleslangs": ["en"],
            "outtmpl": str(tmpdir_path / "%(id)s.%(ext)s"),
        }

        def _try_download(opts, is_auto: bool) -> TranscriptResult:
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
                vtt_files = list(tmpdir_path.glob("*.vtt"))
                if not vtt_files:
                    return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)
                text = _parse_vtt_to_text(vtt_files[0])
                lang = "en"
                return TranscriptResult(text=text, language=lang, is_auto_generated=is_auto)
            except Exception:
                return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)

        manual = _try_download(base_opts, is_auto=False)
        if manual.text:
            return manual

        # Fallback to auto-generated captions.
        auto_opts = dict(base_opts)
        auto_opts["writesubtitles"] = False
        auto_opts["writeautomaticsub"] = True
        auto = _try_download(auto_opts, is_auto=True)
        return auto


def extract_channel_videos_and_transcripts(
    settings: Settings,
    videos: list[ChannelVideo],
    conn,
) -> None:
    """
    Given a list of videos for a channel, ensure they are present in the DB
    and that their transcript status is recorded.
    """
    for video in videos:
        video_id = db.upsert_video(
            conn=conn,
            youtube_id=video.youtube_id,
            title=video.title,
            published_at=video.published_at,
            url=video.url,
        )

        if db.video_has_transcript(conn, video_id):
            continue

        result = fetch_transcript_for_video(video.url)
        if result.text:
            db.store_transcript(
                conn=conn,
                video_id=video_id,
                text=result.text,
                is_auto_generated=result.is_auto_generated,
            )
            db.mark_transcript_status(
                conn=conn,
                video_id=video_id,
                has_transcript=True,
                language=result.language,
            )
        else:
            db.mark_transcript_status(
                conn=conn,
                video_id=video_id,
                has_transcript=False,
                language=None,
            )


