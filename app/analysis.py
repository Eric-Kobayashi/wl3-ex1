from __future__ import annotations

"""
Lightweight post-hoc analysis utilities over the stored database.
"""

from typing import Iterable

from rich.console import Console
from rich.table import Table

from . import db


console = Console()


def print_category_distribution(conn) -> None:
    rows = db.get_category_counts(conn)
    table = Table(title="Category distribution")
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")

    for row in rows:
        table.add_row(str(row["category"]), str(row["count"]))

    console.print(table)


def print_category_distribution_by_month(conn) -> None:
    rows = db.get_category_counts_by_month(conn)
    table = Table(title="Category distribution by month")
    table.add_column("Year-Month", style="bold")
    table.add_column("Category")
    table.add_column("Count", justify="right")

    for row in rows:
        year_month = row["year_month"] or "unknown"
        table.add_row(year_month, str(row["category"]), str(row["count"]))

    console.print(table)


def run_basic_analysis(conn) -> None:
    """
    Basic analysis entry point: prints category counts and distribution over time.
    This is where more advanced manifold / rhetoric analysis can be added later.
    """
    print_category_distribution(conn)
    print_category_distribution_by_month(conn)


