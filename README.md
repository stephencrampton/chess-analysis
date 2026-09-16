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

## Analyze Games

Analyze the downloaded PGN with Stockfish:

```bash
make analyze
```

The results are written to `analysis.csv`. To analyze a different PGN file:

```bash
make analyze PGN=other-games.pgn
```

## Analysis Methodology

The analyzer reads each game from the PGN and examines only moves made by the selected player. For every such move, it asks Stockfish to evaluate the position before the move and the resulting position after the move, using search depth 16 by default. Scores are converted to centipawns from the player's perspective, so the difference represents the loss caused by the played move. Improvements are recorded as zero loss.

Each move is classified by centipawn loss:

- `good`: less than 20 centipawns
- `inaccuracy`: 20 to 49 centipawns
- `mistake`: 50 to 99 centipawns
- `blunder`: 100 centipawns or more

The CSV also records the engine's preferred move and principal variation, position metadata, material balance, game phase, and flags such as captures, checks, castling, and en passant. These classifications are project-defined thresholds and are not intended to reproduce Chess.com's labels.

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
uv run python analyze_games.py --help
```
