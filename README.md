# Chess Analysis

A small utility for downloading recent Chess.com games as a PGN file. The downloader fetches games from the Chess.com public API for a specified username.

## Setup

Install [uv](https://docs.astral.sh/uv/), then install the project dependencies:

```bash
make install
```

This creates the `.venv` virtual environment and installs the dependencies declared in `pyproject.toml`.

## Download Games

Download games with the default username (`stevec-guitar`):

```bash
make download
```

The default target downloads 12 months of games and writes them to `games.pgn`.

Override the username or number of months:

```bash
make download USERNAME=MagnusCarlsen MONTHS=12
```

## Make Commands

```text
make                         Show available commands
make help                    Show available commands
make install                 Create the uv environment and install dependencies
make download                Download games for stevec-guitar
make analyze                 Analyze games.pgn with Stockfish
make all                     Download and analyze games
make format                 Format Python files with Ruff
make clean                   Remove the uv environment and cached files
```

The analysis command requires Stockfish to be installed and available on `PATH`:

```bash
brew install stockfish
```

For direct script options:

```bash
uv run python download_games.py --help
```
