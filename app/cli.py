from __future__ import annotations

"""
Command-line interface entrypoint.
"""

import argparse
import sys

from rich.console import Console

from .config import Settings
from .db import open_db
from .youtube_client import list_channel_videos
from .transcripts import extract_channel_videos_and_transcripts
from .classification import classify_unclassified_transcripts
from .analysis import run_basic_analysis


console = Console()


def _load_settings_or_exit() -> Settings:
    settings = Settings.from_env()
    if not settings.youtube_channel_url:
        console.print(
            "[red]YOUTUBE_CHANNEL_URL is not set.[/red] "
            "Add it to a `.env` file or environment variables."
        )
        sys.exit(1)
    return settings


def cmd_extract(_: argparse.Namespace) -> None:
    """
    Extract phase: list channel videos, download transcripts when available,
    and record transcript status in the local SQLite database.
    """
    settings = _load_settings_or_exit()
    console.print(f"[bold]Extracting videos for channel:[/bold] {settings.youtube_channel_url}")

    videos = list_channel_videos(settings.youtube_channel_url)
    console.print(f"Discovered {len(videos)} videos on the channel.")

    with open_db(settings) as conn:
        extract_channel_videos_and_transcripts(settings, videos, conn)

    console.print("[green]Extraction complete.[/green]")


def cmd_classify(_: argparse.Namespace) -> None:
    """
    Classification phase: classify transcripts into fixed categories.
    """
    settings = _load_settings_or_exit()

    with open_db(settings) as conn:
        count = classify_unclassified_transcripts(settings, conn)

    console.print(f"[green]Classification complete.[/green] Classified {count} transcript(s).")


def cmd_analyze(_: argparse.Namespace) -> None:
    """
    Analysis phase: basic category and temporal distribution summaries.
    """
    settings = _load_settings_or_exit()

    with open_db(settings) as conn:
        run_basic_analysis(conn)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube NLP analysis CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract channel videos and transcripts into the local database.",
    )
    extract_parser.set_defaults(func=cmd_extract)

    classify_parser = subparsers.add_parser(
        "classify",
        help="Classify transcripts into topic categories using an LLM.",
    )
    classify_parser.set_defaults(func=cmd_classify)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run basic post-hoc analysis on the stored data.",
    )
    analyze_parser.set_defaults(func=cmd_analyze)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        sys.exit(1)
    func(args)


if __name__ == "__main__":
    main()


