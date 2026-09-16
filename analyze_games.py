#!/usr/bin/env python3

"""
Analyze all of a player's moves in a PGN using Stockfish.

The output CSV contains one row for every move made by the player,
rather than only mistakes. This allows later analysis for recurring
patterns.

Example:

    uv run python analyze_games.py games.pgn

Defaults:
    player:     stevec-guitar
    depth:      16
    output:     analysis.csv
"""

import argparse
import csv
import shutil
import sys

import chess
import chess.engine
import chess.pgn


DEFAULT_PLAYER = "stevec-guitar"
DEFAULT_DEPTH = 16
DEFAULT_OUTPUT = "analysis.csv"
MATE_SCORE = 100_000
PROGRESS_WIDTH = 30


def score_for_player(info, color):
    """Return engine score in centipawns from the player's perspective."""
    return info["score"].pov(color).score(mate_score=MATE_SCORE)


def mate_for_player(info, color):
    """Return mate distance from the player's perspective, or None."""
    return info["score"].pov(color).mate()


def principal_variation(board, info, max_moves=6):
    """Convert the engine principal variation to a short SAN string."""
    pv = info.get("pv", [])
    temp = board.copy()
    result = []

    for move in pv[:max_moves]:
        if move not in temp.legal_moves:
            break

        result.append(temp.san(move))
        temp.push(move)

    return " ".join(result)


def game_phase(board):
    """Roughly classify a position as opening, middlegame, or endgame."""
    if board.fullmove_number <= 10:
        return "opening"

    values = {
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }

    non_pawn_material = sum(
        (
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
        )
        * value
        for piece_type, value in values.items()
    )

    if non_pawn_material <= 20:
        return "endgame"

    return "middlegame"


def classify_loss(loss):
    """
    Give a simple classification to centipawn loss.

    These classifications are intended for aggregate analysis and do
    not attempt to reproduce Chess.com's classifications.
    """
    if loss < 20:
        return "good"
    if loss < 50:
        return "inaccuracy"
    if loss < 100:
        return "mistake"
    return "blunder"


def material_balance(board, color):
    """Return material balance in pawns from the player's perspective."""
    values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }

    total = 0

    for piece_type, value in values.items():
        total += value * len(board.pieces(piece_type, color))
        total -= value * len(board.pieces(piece_type, not color))

    return total


def load_games(filename):
    """Yield games from a PGN file."""
    with open(filename, encoding="utf-8") as pgn:
        while True:
            game = chess.pgn.read_game(pgn)

            if game is None:
                break

            yield game


def count_games(filename):
    """Count games in a PGN so progress can be reported."""
    return sum(1 for _ in load_games(filename))


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


def analyze_game(engine, game, player, depth):
    """Analyze every move made by player in one game."""
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")

    if white.lower() == player.lower():
        player_color = chess.WHITE
        opponent = black
        player_rating = game.headers.get("WhiteElo", "")
        opponent_rating = game.headers.get("BlackElo", "")
    elif black.lower() == player.lower():
        player_color = chess.BLACK
        opponent = white
        player_rating = game.headers.get("BlackElo", "")
        opponent_rating = game.headers.get("WhiteElo", "")
    else:
        return []

    board = game.board()
    rows = []

    for move in game.mainline_moves():
        if board.turn != player_color:
            board.push(move)
            continue

        move_number = board.fullmove_number
        ply = board.ply() + 1

        fen_before = board.fen()
        phase = game_phase(board)

        san = board.san(move)

        is_capture = board.is_capture(move)
        is_castling = board.is_castling(move)
        is_en_passant = board.is_en_passant(move)

        moved_piece = board.piece_at(move.from_square)
        piece = chess.piece_name(moved_piece.piece_type) if moved_piece else ""

        material_before = material_balance(board, player_color)

        # Evaluate the position before the player's move. This also
        # tells us what Stockfish considers the best continuation.
        before = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
        )

        before_score = score_for_player(before, player_color)
        mate_before = mate_for_player(before, player_color)

        pv = before.get("pv", [])
        best_move = pv[0] if pv else None
        best_san = board.san(best_move) if best_move else ""
        best_pv = principal_variation(board, before)

        played_best_move = move == best_move

        board.push(move)

        gives_check = board.is_check()

        # Evaluate the position resulting from the player's move.
        after = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
        )

        after_score = score_for_player(after, player_color)
        mate_after = mate_for_player(after, player_color)

        # Search depth can cause tiny inconsistencies between the two
        # evaluations, so don't record a negative centipawn loss.
        loss = max(0, before_score - after_score)

        material_after = material_balance(board, player_color)

        rows.append(
            {
                "date": game.headers.get("Date", ""),
                "event": game.headers.get("Event", ""),
                "white": white,
                "black": black,
                "result": game.headers.get("Result", ""),
                "color": "White" if player_color else "Black",
                "opponent": opponent,
                "player_rating": player_rating,
                "opponent_rating": opponent_rating,
                "time_control": game.headers.get("TimeControl", ""),
                "eco": game.headers.get("ECO", ""),
                "opening": game.headers.get("Opening", ""),
                "move_number": move_number,
                "ply": ply,
                "phase": phase,
                "piece": piece,
                "move": san,
                "best_move": best_san,
                "played_best_move": played_best_move,
                "principal_variation": best_pv,
                "eval_before": before_score,
                "eval_after": after_score,
                "centipawn_loss": loss,
                "classification": classify_loss(loss),
                "mate_before": (mate_before if mate_before is not None else ""),
                "mate_after": (mate_after if mate_after is not None else ""),
                "capture": is_capture,
                "check": gives_check,
                "castling": is_castling,
                "en_passant": is_en_passant,
                "material_before": material_before,
                "material_after": material_after,
                "fen": fen_before,
            }
        )

    return rows


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

    print(f"Reading {args.pgn}...", end="", flush=True)
    total_games_in_pgn = count_games(args.pgn)

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
        "event",
        "white",
        "black",
        "result",
        "color",
        "opponent",
        "player_rating",
        "opponent_rating",
        "time_control",
        "eco",
        "opening",
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

    with chess.engine.SimpleEngine.popen_uci(stockfish) as engine:
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

            for game in load_games(args.pgn):
                total_games += 1

                show_progress(
                    total_games,
                    total_games_in_pgn,
                    game_title(game),
                )

                rows = analyze_game(
                    engine,
                    game,
                    args.player,
                    args.depth,
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
