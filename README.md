# wl3-ex1

YouTube NLP analysis CLI built with:

- Pydantic AI (Ollama / OpenAI)
- `youtube-dl`
- SQLite3
- `uv` for dependency management

## Setup

1. Ensure `uv` is installed.
2. From the project root, create the virtual environment and install deps:

```bash
uv sync
```

3. Create a `.env` file in the project root:

```bash
YOUTUBE_CHANNEL_URL=https://www.youtube.com/@YourChannel
LLM_PROVIDER=ollama          # or: openai
OLLAMA_MODEL=llama3.1
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...        # only needed when LLM_PROVIDER=openai
DATABASE_PATH=./youtube_nlp.db
```

## Usage

Run all commands from the project root:

```bash
make extract   # list channel videos, download transcripts if available
make classify  # classify transcripts into topic categories
make analyze   # basic stats and temporal analysis
```

You can also run the CLI directly:

```bash
uv run python -m app.cli extract
```

## Switching LLM providers

The app uses Ollama `llama3.1` by default. To switch to OpenAI, set:

```bash
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...
```
