"""Small wrappers around Stockfish analysis results."""

import chess
import chess.engine
import chess.pgn

MATE_SCORE = 100_000
WHITE = chess.WHITE
BLACK = chess.BLACK
PAWN = chess.PAWN
KNIGHT = chess.KNIGHT
BISHOP = chess.BISHOP
ROOK = chess.ROOK
QUEEN = chess.QUEEN


def open_engine(path):
    """Open a Stockfish engine process."""
    return chess.engine.SimpleEngine.popen_uci(path)


def analyze_position(engine, board, depth):
    """Analyze a position at the requested search depth."""
    return engine.analyse(board, chess.engine.Limit(depth=depth))


def piece_name(piece_type):
    """Return the human-readable name of a chess piece type."""
    return chess.piece_name(piece_type)


def read_game(pgn):
    """Read one game from a PGN stream."""
    return chess.pgn.read_game(pgn)


def score_for_player(info, color):
    """Return an engine score in centipawns from the player's perspective."""
    return info["score"].pov(color).score(mate_score=MATE_SCORE)


def mate_for_player(info, color):
    """Return mate distance from the player's perspective, or None."""
    return info["score"].pov(color).mate()


def principal_variation(board, info, max_moves=6):
    """Convert an engine principal variation to a short SAN string."""
    temp = board.copy()
    moves = []

    for move in info.get("pv", [])[:max_moves]:
        if move not in temp.legal_moves:
            break

        moves.append(temp.san(move))
        temp.push(move)

    return " ".join(moves)
