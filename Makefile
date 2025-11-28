PY := uv run python

.PHONY: extract classify analyze uv-sync

extract:
	$(PY) -m app.cli extract

classify:
	$(PY) -m app.cli classify

analyze:
	$(PY) -m app.cli analyze

uv-sync:
	uv sync



