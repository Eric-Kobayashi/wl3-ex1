from __future__ import annotations

"""
Transcript classification into fixed categories using Pydantic AI.
"""

import asyncio
from typing import Literal

from pydantic import BaseModel, Field

from .config import Settings
from . import db
from .llm import build_agent, describe_model


CATEGORIES = [
    "politics",
    "entertainment",
    "economics",
    "society",
    "culture",
    "others",
]


CategoryLiteral = Literal["politics", "entertainment", "economics", "society", "culture", "others"]


class ClassificationResult(BaseModel):
    category: CategoryLiteral = Field(
        description="Primary category that best describes the overall topic of the transcript."
    )
    rationale: str = Field(
        description="Short explanation for why this category was chosen.",
    )


SYSTEM_PROMPT = """
You classify YouTube talk show episodes into one overall topic category.

Use ONLY one of these categories:
- politics
- entertainment
- economics
- society
- culture
- others

Respond with a single category and a short rationale.
"""


async def _classify_unclassified_transcripts_async(settings: Settings, conn) -> int:
    """
    Async helper to run the classifier over any transcripts that do not have a saved classification.
    """
    agent = build_agent(settings, ClassificationResult, system_prompt=SYSTEM_PROMPT)
    model_name = describe_model(settings)

    classified_count = 0

    for row in db.iter_unclassified_transcripts(conn):
        video_title = row["title"]
        youtube_id = row["youtube_id"]
        transcript_text = row["text"]
        video_id = int(row["video_id"])

        prompt = (
            "You will receive the transcript of a talk show episode.\n"
            "Decide which ONE category from the allowed set best captures the overall topic.\n\n"
            f"Video title: {video_title}\n"
            f"YouTube ID: {youtube_id}\n\n"
            f"Transcript:\n{transcript_text}\n"
        )

        result = await agent.run(prompt)
        data: ClassificationResult = result.output

        db.store_classification(
            conn=conn,
            video_id=video_id,
            category=data.category,
            model=model_name,
            rationale=data.rationale,
        )
        classified_count += 1

    return classified_count


def classify_unclassified_transcripts(settings: Settings, conn) -> int:
    """
    Run the classifier over any transcripts that do not have a saved classification.
    
    This is a synchronous wrapper around the async implementation.
    """
    return asyncio.run(_classify_unclassified_transcripts_async(settings, conn))



