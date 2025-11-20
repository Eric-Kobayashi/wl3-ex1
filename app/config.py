from __future__ import annotations

"""
Configuration loading for the YouTube NLP analysis app.

Reads settings from a `.env` file using `python-dotenv` and from the real
environment, exposing a simple `Settings` object to the rest of the app.
"""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """
    Load environment variables from a `.env` file at project root if present.
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Fallback to default dotenv search if no explicit .env at root.
        load_dotenv()


@dataclass
class Settings:
    """
    Application configuration, sourced from environment variables.

    Required:
      - YOUTUBE_CHANNEL_URL: the URL for the channel to analyze.

    Optional:
      - LLM_PROVIDER: "ollama" or "openai" (default: "ollama").
      - OLLAMA_MODEL: Ollama model name (default: "llama3.1").
      - OPENAI_MODEL: OpenAI model name (default: "gpt-4o-mini").
      - OPENAI_API_KEY: used when LLM_PROVIDER == "openai".
      - DATABASE_PATH: path to the SQLite database file (default: "youtube_nlp.db").
    """

    youtube_channel_url: str
    llm_provider: str = "ollama"
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None
    database_path: Path = PROJECT_ROOT / "youtube_nlp.db"

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        youtube_channel_url = os.getenv("YOUTUBE_CHANNEL_URL", "").strip()

        # Set OLLAMA_BASE_URL if not already set (required by pydantic-ai)
        if "OLLAMA_BASE_URL" not in os.environ:
            os.environ["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        return cls(
            youtube_channel_url=youtube_channel_url,
            llm_provider=os.getenv("LLM_PROVIDER", "ollama").strip() or "ollama",
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1").strip() or "llama3.1",
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434",
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            database_path=Path(
                os.getenv("DATABASE_PATH", str(PROJECT_ROOT / "youtube_nlp.db"))
            ),
        )


