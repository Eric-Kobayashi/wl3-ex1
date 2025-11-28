from __future__ import annotations

"""
SQLite data layer for the YouTube NLP analysis app.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .config import Settings


@dataclass
class VideoRecord:
    id: int
    youtube_id: str
    title: str
    published_at: str
    url: str
    has_transcript: int
    transcript_language: Optional[str]


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def get_connection(settings: Settings) -> sqlite3.Connection:
    """
    Open a SQLite3 connection to the configured database path.
    """
    db_path: Path = settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Ensure all tables exist.
    """
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            youtube_id TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            published_at TEXT,
            url TEXT NOT NULL,
            has_transcript INTEGER NOT NULL DEFAULT 0,
            transcript_language TEXT,
            created_at TEXT NOT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_auto_generated INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS classifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            model TEXT NOT NULL,
            rationale TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
        );
        """
    )

    conn.commit()


def upsert_video(
    conn: sqlite3.Connection,
    youtube_id: str,
    title: str,
    published_at: Optional[str],
    url: str,
) -> int:
    """
    Insert or update a video row and return its internal id.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO videos (youtube_id, title, published_at, url, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(youtube_id) DO UPDATE SET
            title = excluded.title,
            published_at = excluded.published_at,
            url = excluded.url
        ;
        """,
        (youtube_id, title, published_at, url, _utc_now_iso()),
    )
    conn.commit()

    cursor.execute(
        "SELECT id FROM videos WHERE youtube_id = ?",
        (youtube_id,),
    )
    row = cursor.fetchone()
    assert row is not None
    return int(row["id"])


def mark_transcript_status(
    conn: sqlite3.Connection,
    video_id: int,
    has_transcript: bool,
    language: Optional[str],
) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE videos
        SET has_transcript = ?, transcript_language = ?
        WHERE id = ?
        """,
        (1 if has_transcript else 0, language, video_id),
    )
    conn.commit()


def store_transcript(
    conn: sqlite3.Connection,
    video_id: int,
    text: str,
    is_auto_generated: bool,
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transcripts (video_id, text, is_auto_generated, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (video_id, text, 1 if is_auto_generated else 0, _utc_now_iso()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def video_has_transcript(conn: sqlite3.Connection, video_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT has_transcript FROM videos WHERE id = ?",
        (video_id,),
    )
    row = cursor.fetchone()
    return bool(row and row["has_transcript"])


def iter_unclassified_transcripts(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    """
    Yield transcripts that do not yet have a classification row.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            v.id AS video_id,
            v.youtube_id,
            v.title,
            v.published_at,
            v.url,
            t.id AS transcript_id,
            t.text
        FROM videos v
        JOIN transcripts t ON t.video_id = v.id
        LEFT JOIN classifications c ON c.video_id = v.id
        WHERE c.id IS NULL
        ORDER BY v.published_at IS NULL, v.published_at
        """
    )
    for row in cursor.fetchall():
        yield row


def store_classification(
    conn: sqlite3.Connection,
    video_id: int,
    category: str,
    model: str,
    rationale: Optional[str],
) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO classifications (video_id, category, model, rationale, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (video_id, category, model, rationale, _utc_now_iso()),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_category_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT category, COUNT(*) AS count
        FROM classifications
        GROUP BY category
        ORDER BY count DESC
        """
    )
    return cursor.fetchall()


def get_category_counts_by_month(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """
    Aggregate category counts per YYYY-MM bucket based on video.published_at.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            substr(v.published_at, 1, 7) AS year_month,
            c.category,
            COUNT(*) AS count
        FROM classifications c
        JOIN videos v ON v.id = c.video_id
        WHERE v.published_at IS NOT NULL
        GROUP BY year_month, c.category
        ORDER BY year_month, c.category
        """
    )
    return cursor.fetchall()


@contextmanager
def open_db(settings: Settings) -> Iterator[sqlite3.Connection]:
    """
    Convenience context manager that opens and initializes the database.
    """
    conn = get_connection(settings)
    try:
        init_db(conn)
        yield conn
    finally:
        conn.close()



