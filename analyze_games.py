#!/usr/bin/env python3

"""
Analyze Chess.com games with Stockfish and report objectively bad moves.

Example:

    uv run python analyze_games.py games.pgn

By default:
    - player is stevec-guitar
    - moves losing >= 50 centipawns are reported
    - Stockfish analyzes each position to depth 16
    - results are written to mistakes.csv
"""

import argparse
import csv
import shutil
import sys

import chess
import chess.engine
import chess.pgn


DEFAULT_PLAYER = "stevec-guitar"
DEFAULT_THRESHOLD = 50
DEFAULT_DEPTH = 16
DEFAULT_OUTPUT = "mistakes.csv"


def score_for_player(info, color):
    """Convert Stockfish's score to centipawns from player's perspective."""
    score = info["score"].pov(color)

    # Treat a forced mate as a very large evaluation.
    return score.score(mate_score=100_000)


def analyze_game(engine, game, player, depth, threshold):
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")

    if white.lower() == player.lower():
        player_color = chess.WHITE
        opponent = black
    elif black.lower() == player.lower():
        player_color = chess.BLACK
        opponent = white
    else:
        return []

    board = game.board()
    mistakes = []

    for move in game.mainline_moves():
        is_player_move = board.turn == player_color

        if not is_player_move:
            board.push(move)
            continue

        move_number = board.fullmove_number
        san = board.san(move)
        fen = board.fen()

        # Analyze the position before our move.
        before = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
        )

        before_score = score_for_player(before, player_color)

        pv = before.get("pv", [])
        best_move = pv[0] if pv else None
        best_san = board.san(best_move) if best_move else ""

        board.push(move)

        # Analyze the resulting position.
        after = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
        )

        after_score = score_for_player(after, player_color)

        loss = before_score - after_score

        if loss >= threshold:
            mistakes.append(
                {
                    "date": game.headers.get("Date", ""),
                    "white": white,
                    "black": black,
                    "result": game.headers.get("Result", ""),
                    "color": "White" if player_color else "Black",
                    "opponent": opponent,
                    "move_number": move_number,
                    "move": san,
                    "best_move": best_san,
                    "eval_before": before_score,
                    "eval_after": after_score,
                    "centipawn_loss": loss,
                    "fen": fen,
                }
            )

    return mistakes


def load_games(filename):
    with open(filename, encoding="utf-8") as pgn:
        while True:
            game = chess.pgn.read_game(pgn)

            if game is None:
                break

            yield game


def main():
    parser = argparse.ArgumentParser(
        description="Find objectively bad moves in Chess.com games."
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
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=(f"Minimum centipawn loss to report (default: {DEFAULT_THRESHOLD})"),
    )

    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"CSV output file (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

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

    fields = [
        "date",
        "white",
        "black",
        "result",
        "color",
        "opponent",
        "move_number",
        "move",
        "best_move",
        "eval_before",
        "eval_after",
        "centipawn_loss",
        "fen",
    ]

    total_games = 0
    total_mistakes = 0

    with chess.engine.SimpleEngine.popen_uci(stockfish) as engine:
        with open(
            args.output,
            "w",
            newline="",
            encoding="utf-8",
        ) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()

            for game in load_games(args.pgn):
                total_games += 1

                white = game.headers.get("White", "?")
                black = game.headers.get("Black", "?")

                print(
                    f"\rAnalyzing game {total_games}: {white} vs {black}",
                    end="",
                    flush=True,
                )

                mistakes = analyze_game(
                    engine,
                    game,
                    args.player,
                    args.depth,
                    args.threshold,
                )

                for mistake in mistakes:
                    writer.writerow(mistake)

                total_mistakes += len(mistakes)

    print()
    print(
        f"Analyzed {total_games} games; "
        f"found {total_mistakes} moves losing at least "
        f"{args.threshold} cp."
    )
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
