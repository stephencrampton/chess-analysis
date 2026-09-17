import chess
import chess.engine

from chess_analysis.engine import (
    BLACK,
    WHITE,
    analyze_position,
    mate_for_player,
    piece_name,
    principal_variation,
    score_for_player,
)


def test_engine_adapters_convert_scores_and_piece_names():
    info = {"score": chess.engine.PovScore(chess.engine.Cp(34), WHITE)}

    assert score_for_player(info, WHITE) == 34
    assert score_for_player(info, BLACK) == -34
    assert mate_for_player(info, WHITE) is None
    assert piece_name(chess.PAWN) == "pawn"


def test_engine_adapters_handle_mate_and_principal_variation():
    mate_info = {"score": chess.engine.PovScore(chess.engine.Mate(3), WHITE)}
    assert mate_for_player(mate_info, WHITE) == 3
    assert score_for_player(mate_info, WHITE) == 99997

    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    assert principal_variation(board, {"pv": [move]}, max_moves=1) == "e4"
    assert principal_variation(board, {"pv": [chess.Move.from_uci("a1a8")]}) == ""


def test_analyze_position_passes_depth_to_engine():
    class FakeEngine:
        def analyse(self, board, limit):
            return limit

    result = analyze_position(FakeEngine(), chess.Board(), depth=7)

    assert result.depth == 7
