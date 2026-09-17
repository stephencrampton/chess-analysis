UV ?= uv
USERNAME ?= stevec-guitar
MONTHS ?= 3
PGN ?=
ANALYSIS ?=
WORKERS ?= 4

.DEFAULT_GOAL := help

.PHONY: help install clean format test download analyze summarize visualize all

help:
	@echo 'Available commands:'
	@printf '  %-24s %s\n' 'make install' 'Create the uv environment and install dependencies'
	@printf '  %-24s %s\n' 'make download' 'Download 3 months of games'
	@printf '  %-24s %s\n' 'make download MONTHS=12' 'Download a custom number of months'
	@printf '  %-24s %s\n' 'make analyze' 'Analyze the newest PGN with Stockfish'
	@printf '  %-24s %s\n' 'make analyze PGN=file.pgn' 'Analyze a specific PGN'
	@printf '  %-24s %s\n' 'make analyze WORKERS=8' 'Analyze games with 8 workers'
	@printf '  %-24s %s\n' 'make summarize' 'Summarize the newest analysis CSV'
	@printf '  %-24s %s\n' 'make summarize ANALYSIS=file.csv' 'Summarize a specific analysis CSV'
	@printf '  %-24s %s\n' 'make visualize' 'Generate a standalone browser UI'
	@printf '  %-24s %s\n' 'make visualize ANALYSIS=file.csv' 'Visualize a specific analysis CSV'
	@printf '  %-24s %s\n' 'make all' 'Download and analyze games'
	@printf '  %-24s %s\n' 'make format' 'Format Python files with Ruff'
	@printf '  %-24s %s\n' 'make test' 'Run unit tests with coverage'
	@printf '  %-24s %s\n' 'make clean' 'Remove the uv environment and cached files'

install:
	@if [ ! -d .venv ]; then $(UV) venv; fi
	$(UV) sync

clean:
	$(UV) cache clean
	rm -rf .venv
	rm -f .coverage* coverage.xml
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

format:
	$(UV) run ruff format .

test:
	$(UV) run pytest --cov=chess_analysis --cov-report=term-missing

download:
	@username=$$(printf '%s' "$(USERNAME)" | tr '[:upper:]' '[:lower:]'); \
	$(UV) run python -m chess_analysis.download_games "$$username" --months $(MONTHS)

analyze:
	@pgn="$(PGN)"; \
	if [ -z "$$pgn" ]; then pgn=$$(ls -t games_*.pgn 2>/dev/null | head -1); fi; \
	if [ -z "$$pgn" ]; then echo 'No PGN found; pass PGN=filename.pgn' >&2; exit 1; fi; \
	$(UV) run python -m chess_analysis.analyze_games "$$pgn" --workers $(WORKERS)

summarize:
	@analysis="$(ANALYSIS)"; \
	if [ -z "$$analysis" ]; then analysis=$$(ls -t analysis_*.csv 2>/dev/null | head -1); fi; \
	if [ -z "$$analysis" ]; then echo 'No analysis CSV found; pass a filename to the Python module' >&2; exit 1; fi; \
	$(UV) run python -m chess_analysis.summarize "$$analysis"

visualize:
	@analysis="$(ANALYSIS)"; \
	if [ -z "$$analysis" ]; then analysis=$$(ls -t analysis_*.csv 2>/dev/null | head -1); fi; \
	if [ -z "$$analysis" ]; then echo 'No analysis CSV found; pass ANALYSIS=filename.csv' >&2; exit 1; fi; \
	$(UV) run python -m chess_analysis.visualize "$$analysis"

all: download
	$(MAKE) analyze