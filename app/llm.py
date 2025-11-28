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
    from pydantic_ai.models import infer_model
    from pydantic_ai.providers import infer_provider
    
    # Ensure OLLAMA_BASE_URL is set before getting model string (which may use Ollama)
    if settings.llm_provider.lower() != "openai":
        if "OLLAMA_BASE_URL" not in os.environ:
            os.environ["OLLAMA_BASE_URL"] = settings.ollama_base_url
    
    model_string = _get_model_string(settings)
    
    # For Ollama, we need to explicitly pass the provider factory
    # because infer_model doesn't correctly parse "ollama:model_name" format
    if settings.llm_provider.lower() == "ollama":
        provider = infer_provider("ollama")
        def provider_factory(name: str):
            if name == "ollama":
                return provider
            return infer_provider(name)
        
        # Infer model with explicit provider factory
        model = infer_model(model_string, provider_factory=provider_factory)
        agent = Agent(
            model=model,
            output_type=output_type,
            system_prompt=system_prompt,
        )
    else:
        # For OpenAI, we can use the string directly
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


