from __future__ import annotations

"""
Transcript discovery and download using `yt_dlp`.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import time
import random

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

        def _try_download(opts, is_auto: bool, max_retries: int = 3) -> TranscriptResult:
            """
            Try to download transcript with retry logic for rate limiting.
            
            Handles HTTP 429 (Too Many Requests) with exponential backoff.
            """
            for attempt in range(max_retries):
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.extract_info(url, download=True)
                    vtt_files = list(tmpdir_path.glob("*.vtt"))
                    if not vtt_files:
                        return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)
                    text = _parse_vtt_to_text(vtt_files[0])
                    lang = "en"
                    return TranscriptResult(text=text, language=lang, is_auto_generated=is_auto)
                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    # Check if it's a 429 rate limit error
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        if attempt < max_retries - 1:
                            # Exponential backoff: 2^attempt seconds, with jitter
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            time.sleep(wait_time)
                            continue
                        # If we've exhausted retries, return None
                        return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)
                    # For other errors, return None immediately
                    return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)
                except Exception:
                    # For any other exception, return None
                    return TranscriptResult(text=None, language=None, is_auto_generated=is_auto)
            
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
    
    Includes rate limiting with delays between requests to avoid hitting
    YouTube's rate limits (HTTP 429 errors).
    """
    from rich.console import Console
    
    console = Console()
    total = len(videos)
    processed = 0
    transcripts_found = 0
    transcripts_missing = 0
    
    for idx, video in enumerate(videos, 1):
        video_id = db.upsert_video(
            conn=conn,
            youtube_id=video.youtube_id,
            title=video.title,
            published_at=video.published_at,
            url=video.url,
        )

        if db.video_has_transcript(conn, video_id):
            processed += 1
            continue

        # Add delay between requests to avoid rate limiting
        # Random delay between 1-3 seconds to avoid predictable patterns
        if idx > 1:  # Don't delay before the first request
            delay = random.uniform(1.0, 3.0)
            time.sleep(delay)

        console.print(f"[dim]Processing video {idx}/{total}: {video.title[:50]}...[/dim]")
        
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
            transcripts_found += 1
        else:
            db.mark_transcript_status(
                conn=conn,
                video_id=video_id,
                has_transcript=False,
                language=None,
            )
            transcripts_missing += 1
        
        processed += 1
    
    console.print(
        f"[green]Processed {processed}/{total} videos. "
        f"Transcripts found: {transcripts_found}, Missing: {transcripts_missing}[/green]"
    )


