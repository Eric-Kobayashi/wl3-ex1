from __future__ import annotations

"""
Thin wrapper around `yt_dlp` to list videos for a channel.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import yt_dlp


@dataclass
class ChannelVideo:
    youtube_id: str
    title: str
    url: str
    published_at: Optional[str]


def _normalize_upload_date(upload_date: Optional[str]) -> Optional[str]:
    """
    Convert YouTube's YYYYMMDD upload_date string to ISO YYYY-MM-DD.
    """
    if not upload_date:
        return None
    try:
        dt = datetime.strptime(upload_date, "%Y%m%d")
        return dt.date().isoformat()
    except Exception:
        return None


def list_channel_videos(channel_url: str) -> List[ChannelVideo]:
    """
    Return basic metadata for all videos in a channel.
    """
    ydl_opts = {
        "ignoreerrors": True,
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "dump_single_json": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url, download=False)
        except Exception as e:
            raise RuntimeError(
                f"Failed to extract channel information from {channel_url}. "
                f"Error: {e}"
            ) from e

    if info is None:
        raise RuntimeError(
            f"Failed to extract channel information from {channel_url}. "
            "yt-dlp returned None. The channel URL may be invalid or the channel may be private."
        )

    entries = info.get("entries") or []
    videos: List[ChannelVideo] = []

    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        title = entry.get("title") or ""
        upload_date = _normalize_upload_date(entry.get("upload_date"))
        if not video_id:
            continue

        url = f"https://www.youtube.com/watch?v={video_id}"
        videos.append(
            ChannelVideo(
                youtube_id=video_id,
                title=title,
                url=url,
                published_at=upload_date,
            )
        )

    return videos


