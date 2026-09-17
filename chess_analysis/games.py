"""PGN loading helpers."""

from chess_analysis.engine import read_game


def load_games(filename):
    """Yield games from a PGN file."""
    with open(filename, encoding="utf-8") as pgn:
        while game := read_game(pgn):
            yield game


def count_games(filename):
    """Count games in a PGN so progress can be reported."""
    return sum(1 for _ in load_games(filename))
