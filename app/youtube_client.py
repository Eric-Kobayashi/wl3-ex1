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


def _extract_videos_from_entries(entries: list, videos: List[ChannelVideo]) -> None:
    """
    Recursively extract video entries from a potentially nested entries structure.
    Handles channels that have sections (Videos, Live, Shorts) with nested entries.
    """
    for entry in entries:
        if not entry:
            continue
        
        # If this entry has nested entries (like a playlist/section), recurse
        if entry.get("entries"):
            _extract_videos_from_entries(entry.get("entries"), videos)
            continue
        
        # Extract video information
        video_id = entry.get("id")
        if not video_id:
            # Try to extract from URL
            url = entry.get("url") or entry.get("webpage_url") or ""
            if "watch?v=" in url:
                video_id = url.split("watch?v=")[-1].split("&")[0].split("/")[0]
            else:
                continue
        
        title = entry.get("title") or ""
        upload_date = _normalize_upload_date(entry.get("upload_date"))
        
        # Construct URL if not present
        if not entry.get("url") and not entry.get("webpage_url"):
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            url = entry.get("url") or entry.get("webpage_url")

        videos.append(
            ChannelVideo(
                youtube_id=video_id,
                title=title,
                url=url,
                published_at=upload_date,
            )
        )


def list_channel_videos(channel_url: str, max_videos: int = 100) -> List[ChannelVideo]:
    """
    Return basic metadata for videos in a channel.
    
    Uses yt-dlp to extract videos from the channel. By default, extracts the
    most recent 100 videos. Set max_videos to None to get all videos (may take
    a long time for channels with many videos).
    
    If the channel URL is a handle (e.g., @channelname), it will automatically
    use the /videos endpoint to get videos.
    
    Args:
        channel_url: URL of the YouTube channel
        max_videos: Maximum number of videos to extract (default: 100)
    """
    # Convert channel handle to videos URL if needed
    if channel_url.startswith("https://www.youtube.com/@") and "/videos" not in channel_url:
        channel_url = channel_url.rstrip("/") + "/videos"
    
    ydl_opts = {
        "ignoreerrors": True,
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,  # Get full metadata
        "no_warnings": False,
    }
    
    # Limit to max_videos if specified
    if max_videos is not None:
        ydl_opts["playlistend"] = max_videos

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Extract info for the channel (this will get all videos)
            info = ydl.extract_info(channel_url, download=False, process=True)
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
    
    # Recursively extract all videos from potentially nested entries
    _extract_videos_from_entries(entries, videos)
    
    # Limit to max_videos if we got more than requested
    if max_videos is not None and len(videos) > max_videos:
        videos = videos[:max_videos]

    return videos


