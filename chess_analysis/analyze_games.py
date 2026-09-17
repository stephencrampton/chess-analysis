#!/usr/bin/env python3

"""
Analyze all of a player's moves in a PGN using Stockfish.

The output CSV contains one row for every move made by the player,
rather than only mistakes. This allows later analysis for recurring
patterns.

Example:

    uv run python -m chess_analysis.analyze_games games_YYYYMMDD_HHMMSS.pgn

Defaults:
    player:     stevec-guitar
    depth:      16
    output:     timestamped analysis CSV
"""

import argparse
import csv
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor

from chess_analysis.engine import open_engine
from chess_analysis.filenames import timestamped_filename
from chess_analysis.games import load_games
from chess_analysis.move_analysis import analyze_game

DEFAULT_PLAYER = "stevec-guitar"
DEFAULT_DEPTH = 16
DEFAULT_WORKERS = min(4, os.cpu_count() or 1)
PROGRESS_WIDTH = 30
_worker_engine = None


def close_worker_engine():
    """Close the Stockfish process owned by this worker, if any."""
    global _worker_engine
    if _worker_engine is not None:
        _worker_engine.quit()
        _worker_engine = None


def initialize_worker(stockfish):
    """Open one independent Stockfish process in each pool worker."""
    global _worker_engine

    _worker_engine = open_engine(stockfish)


def analyze_game_in_worker(task):
    """Analyze one game using the worker's process-local engine."""
    game, player, depth = task
    return analyze_game(_worker_engine, game, player, depth)


def shutdown_worker():
    """Quit the worker's Stockfish process before the pool exits."""
    close_worker_engine()


def game_title(game):
    """Return a human-readable title with ratings and winner."""
    white = game.headers.get("White", "?")
    black = game.headers.get("Black", "?")
    white_rating = game.headers.get("WhiteElo", "?")
    black_rating = game.headers.get("BlackElo", "?")
    result = game.headers.get("Result", "*")

    if result == "1-0":
        white += "*"
    elif result == "0-1":
        black += "*"

    return f"{white} ({white_rating}) vs {black} ({black_rating})"


def show_progress(current, total, title, width=PROGRESS_WIDTH):
    """Display an in-place progress bar and current game title."""
    fraction = current / total if total else 1.0
    completed = int(width * fraction)

    bar = "█" * completed + "░" * (width - completed)

    status = f"[{bar}] {current:>{len(str(total))}}/{total}  {title}"

    # Return to the beginning of the line, then erase the entire line
    # before writing the new status. This prevents characters from a
    # longer previous game title from remaining on screen.
    print(f"\r\033[2K{status}", end="", flush=True)


def clear_progress():
    """Erase the progress line."""
    print("\r\033[2K", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a player's Chess.com games with Stockfish."
    )

    parser.add_argument(
        "pgn",
        help="PGN file containing Chess.com games",
    )

    parser.add_argument(
        "--player",
        default=DEFAULT_PLAYER,
        help=f"Chess.com username (default: {DEFAULT_PLAYER})",
    )

    parser.add_argument(
        "--stockfish",
        default="stockfish",
        help="Stockfish executable (default: stockfish)",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Stockfish search depth (default: {DEFAULT_DEPTH})",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="CSV output file (default: timestamped analysis file)",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Stockfish worker processes (default: {DEFAULT_WORKERS})",
    )

    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")

    if args.output is None:
        args.output = timestamped_filename("analysis", "csv")

    stockfish = shutil.which(args.stockfish)

    if stockfish is None:
        print(
            f"Cannot find Stockfish executable: {args.stockfish}",
            file=sys.stderr,
        )
        print(
            "On macOS, try: brew install stockfish",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Reading {args.pgn}...", end="", flush=True)
    games = list(load_games(args.pgn))
    total_games_in_pgn = len(games)

    if total_games_in_pgn == 0:
        print()
        print(
            f"No games found in {args.pgn}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f" {total_games_in_pgn} games")

    fields = [
        "date",
        "result",
        "color",
        "opponent",
        "my_rating",
        "opponent_rating",
        "time_since_my_last_move",
        "time_since_my_opponents_move",
        "my_time_remaining",
        "move_number",
        "ply",
        "phase",
        "piece",
        "move",
        "best_move",
        "played_best_move",
        "principal_variation",
        "eval_before",
        "eval_after",
        "centipawn_loss",
        "classification",
        "mate_before",
        "mate_after",
        "capture",
        "check",
        "castling",
        "en_passant",
        "material_before",
        "material_after",
        "fen",
    ]

    total_games = 0
    total_moves = 0
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0

    with open(
        args.output,
        "w",
        newline="",
        encoding="utf-8",
    ) as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=fields,
        )
        writer.writeheader()

        tasks = ((game, args.player, args.depth) for game in games)
        with ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=initialize_worker,
            initargs=(stockfish,),
        ) as executor:
            results = executor.map(analyze_game_in_worker, tasks)

            for game, rows in zip(games, results):
                total_games += 1

                show_progress(
                    total_games,
                    total_games_in_pgn,
                    game_title(game),
                )

                for row in rows:
                    writer.writerow(row)
                    total_moves += 1

                    classification = row["classification"]

                    if classification == "blunder":
                        total_blunders += 1
                    elif classification == "mistake":
                        total_mistakes += 1
                    elif classification == "inaccuracy":
                        total_inaccuracies += 1

            shutdowns = [executor.submit(shutdown_worker) for _ in range(args.workers)]
            for shutdown in shutdowns:
                shutdown.result()

    clear_progress()

    print(f"Analyzed {total_games} games and {total_moves} moves.")
    print(
        f"{total_blunders} blunders, "
        f"{total_mistakes} mistakes, "
        f"{total_inaccuracies} inaccuracies."
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
