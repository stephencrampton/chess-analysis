# Chess Analysis

A tool for analyzing a player's Chess.com games to identify **recurring patterns of mistakes that can be improved**.

The goal is not simply to find individual blunders. Chess engines already do that very well. Instead, this project collects objective Stockfish analysis across many games so that recurring weaknesses can be identified, such as:

* making more mistakes in the opening, middlegame, or endgame;
* repeatedly mishandling particular openings or types of positions;
* making errors when ahead or behind in material;
* making disproportionately costly moves with particular pieces;
* overlooking tactics after captures, checks, or other forcing moves;
* consistently choosing certain kinds of moves when Stockfish prefers something else; and
* other statistical patterns that may suggest specific areas to practice.

The intended workflow is:

```text
Chess.com
    ↓
    games_YYYYMMDD_HHMMSS.pgn
    ↓
Stockfish analysis
    ↓
    analysis_YYYYMMDD_HHMMSS.csv
    ↓
pattern analysis
    ↓
actionable areas for improvement
```

## Setup

Install `uv` and Stockfish:

```bash
brew install uv stockfish
```

Then install the project dependencies:

```bash
make install
```

This creates the `.venv` virtual environment and installs the dependencies declared in `pyproject.toml`.

## Download Games

Download games with the default Chess.com username (`stevec-guitar`):

```bash
make download
```

The default target downloads 12 months of games and writes them to a timestamped file such as:

```text
games_20260916_143012.pgn
```

The timestamp prevents a later download from overwriting an earlier one. Pass
`--output` to choose a specific filename.

Override the username or number of months:

```bash
make download USERNAME=MagnusCarlsen MONTHS=12
```

## Analyze Games

Download and analyze the latest games in one step:

```bash
make all
```

To analyze a specific downloaded PGN, pass its filename:

```bash
make analyze PGN=games_20260916_143012.pgn
```

Analysis can take some time because Stockfish evaluates the position before and after every move made by the selected player.

While running, the analyzer displays a progress bar and the game currently being analyzed:

```text
[████████████████░░░░░░░░]  67/100  stevec-guitar vs opponent
```

The results are written to a timestamped file such as:

```text
analysis_20260916_143012.csv
```

The timestamp prevents a later run from overwriting an earlier result. Pass
`--output` to choose a specific filename.

To analyze a different PGN file:

```bash
make analyze PGN=other-games.pgn
```

## Analysis Methodology

The analyzer reads each game from the PGN and examines only moves made by the selected player.

For every player move, Stockfish evaluates:

1. the position immediately before the move; and
2. the resulting position immediately after the move.

Stockfish uses search depth 16 by default.

Scores are converted to centipawns from the player's perspective. The difference between the evaluations represents the approximate value lost by the played move. If the resulting evaluation is better, the loss is recorded as zero.

Every move is retained in the CSV, not just mistakes. This is important for pattern analysis. For example, knowing that ten bad rook moves occurred is much more useful when we also know how many rook moves were made successfully.

### Move classifications

Moves are given simple project-defined classifications based on centipawn loss:

| Classification | Centipawn loss |
| -------------- | -------------: |
| `good`         |           < 20 |
| `inaccuracy`   |          20–49 |
| `mistake`      |          50–99 |
| `blunder`      |          ≥ 100 |

These classifications are intended for aggregate analysis and do **not** attempt to reproduce Chess.com's move classifications.

### Recorded information

For each player move, the timestamped analysis CSV includes information such as:

* game date and result;
* player color;
* opponent;
* player and opponent ratings;
* time spent on the player's previous move, time spent on the opponent's previous move, and the player's remaining time;
* move number;
* game phase;
* piece moved;
* move played;
* Stockfish's preferred move;
* whether the preferred move was played;
* Stockfish's principal variation;
* evaluation before and after the move;
* centipawn loss;
* move classification;
* mate evaluations;
* whether the move was a capture, check, castle, or en passant;
* material balance; and
* the FEN of the position before the move.

Keeping this richer dataset makes it possible to look for correlations and recurring weaknesses rather than treating each engine mistake as an isolated event.

## Future Pattern Analysis

The next stage of the project is to analyze the timestamped analysis CSV across many games.

Potential reports include:

* error rate and average centipawn loss by game phase;
* error rate by piece;
* performance as White versus Black;
* mistakes by move number;
* mistakes when ahead, equal, or behind;
* frequency of large evaluation swings;
* recurring positions or tactical themes;
* performance by opponent strength; and
* changes in these measures over time.

The aim is to turn engine output into observations such as:

> A disproportionate share of large mistakes occurs shortly after leaving the opening.

or:

> Positions in which the player is materially ahead have an unusually high rate of 100+ centipawn errors.

Those observations can then suggest specific things to study or habits to change.

## Make Commands

```text
make                         Show available commands
make help                    Show available commands
make install                 Create the uv environment and install dependencies
make download                Download games for stevec-guitar
make analyze                 Analyze a PGN with Stockfish
make all                     Download and analyze games
make format                  Format Python files with Ruff
make clean                   Remove the uv environment and cached files
```

For direct module options:

```bash
uv run python -m chess_analysis.download_games --help
uv run python -m chess_analysis.analyze_games --help
```
