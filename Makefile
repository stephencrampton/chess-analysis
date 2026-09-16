UV ?= uv
USERNAME ?= stevec-guitar
MONTHS ?= 12
PGN ?= games.pgn

.DEFAULT_GOAL := help

.PHONY: help install clean format download analyze all

help:
	@echo 'Available commands:'
	@echo '  make install                                  Create the uv environment and install dependencies'
	@echo '  make download                                 Download 12 months of games'
	@echo '  make analyze                                  Analyze games.pgn with Stockfish'
	@echo '  make all                                      Download and analyze games'
	@echo '  make format                                  Format Python files with Ruff'
	@echo '  make clean                                    Remove the uv environment and cached files'

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
	$(UV) run python download_games.py "$$username" --months $(MONTHS)

analyze:
	$(UV) run python analyze_games.py $(PGN)

all: download analyze