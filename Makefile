UV ?= uv
USERNAME ?= stevec-guitar
MONTHS ?= 12
PGN ?=

.DEFAULT_GOAL := help

.PHONY: help install clean format download analyze all

help:
	@echo 'Available commands:'
	@printf '  %-24s %s\n' 'make install' 'Create the uv environment and install dependencies'
	@printf '  %-24s %s\n' 'make download' 'Download 12 months of games'
	@printf '  %-24s %s\n' 'make analyze' 'Analyze the newest PGN with Stockfish'
	@printf '  %-24s %s\n' 'make all' 'Download and analyze games'
	@printf '  %-24s %s\n' 'make format' 'Format Python files with Ruff'
	@printf '  %-24s %s\n' 'make clean' 'Remove the uv environment and cached files'

install:
	@if [ ! -d .venv ]; then $(UV) venv; fi
	$(UV) sync

clean:
	$(UV) cache clean
	rm -rf .venv
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

format:
	$(UV) run ruff format .

download:
	@username=$$(printf '%s' "$(USERNAME)" | tr '[:upper:]' '[:lower:]'); \
	$(UV) run python -m chess_analysis.download_games "$$username" --months $(MONTHS)

analyze:
	@pgn="$(PGN)"; \
	if [ -z "$$pgn" ]; then pgn=$$(ls -t games_*.pgn 2>/dev/null | head -1); fi; \
	if [ -z "$$pgn" ]; then echo 'No PGN found; pass PGN=filename.pgn' >&2; exit 1; fi; \
	$(UV) run python -m chess_analysis.analyze_games "$$pgn"

all: download
	$(MAKE) analyze