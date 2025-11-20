from __future__ import annotations

"""
Pydantic AI model configuration for Ollama and OpenAI backends.
"""

import os
from typing import Type

from pydantic import BaseModel
from pydantic_ai import Agent

from .config import Settings


def _get_model_string(settings: Settings) -> str:
    """
    Get the model string identifier for Pydantic AI.
    
    Format: "provider:model_name" (e.g., "ollama:llama3.1" or "openai:gpt-4o-mini")
    """
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return f"openai:{settings.openai_model}"
    # Default to Ollama - ensure OLLAMA_BASE_URL is set
    if "OLLAMA_BASE_URL" not in os.environ:
        os.environ["OLLAMA_BASE_URL"] = settings.ollama_base_url
    return f"ollama:{settings.ollama_model}"


def build_agent(settings: Settings, output_type: Type[BaseModel], system_prompt: str) -> Agent:
    """
    Construct a Pydantic AI Agent for structured outputs.
    
    The Agent accepts a string model identifier in the format "provider:model_name".
    """
    model_string = _get_model_string(settings)
    agent = Agent(
        model=model_string,
        output_type=output_type,
        system_prompt=system_prompt,
    )
    return agent


def describe_model(settings: Settings) -> str:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return f"openai:{settings.openai_model}"
    return f"ollama:{settings.ollama_model}"


