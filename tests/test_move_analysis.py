import chess
import chess.pgn
from io import StringIO

from chess_analysis.engine import BLACK, WHITE
import chess_analysis.move_analysis as move_analysis
from chess_analysis.move_analysis import (
    analyze_game,
    classify_loss,
    game_phase,
    material_balance,
    parse_clock,
    result_for_player,
)


def test_parse_clock_returns_seconds_and_rejects_invalid_comments():
    assert parse_clock("[%clk 1:02:03.5]") == 3723.5
    assert parse_clock("a comment without a clock") is None
    assert parse_clock("[%clk 1:02]") is None


def test_result_for_player_handles_wins_draws_and_timeouts():
    game = chess.pgn.Game()
    game.headers.update({"Result": "1-0", "Termination": "Normal"})

    assert result_for_player(game, WHITE) == "win"
    assert result_for_player(game, BLACK) == "loss"

    game.headers["Result"] = "1/2-1/2"
    assert result_for_player(game, WHITE) == "draw"

    game.headers["Termination"] = "Time forfeit"
    assert result_for_player(game, WHITE) == "timeout"


def test_classify_loss_uses_expected_boundaries():
    assert [classify_loss(loss) for loss in (0, 19.99, 20, 49.99, 50, 99.99, 100)] == [
        "good",
        "good",
        "inaccuracy",
        "inaccuracy",
        "mistake",
        "mistake",
        "blunder",
    ]


def test_game_phase_and_material_balance_describe_a_position():
    board = chess.Board()
    assert game_phase(board) == "opening"
    assert material_balance(board, WHITE) == 0

    board = chess.Board("8/8/8/8/8/8/4P3/4K2k w - - 0 11")
    assert game_phase(board) == "endgame"
    assert material_balance(board, WHITE) == 1
    assert material_balance(board, BLACK) == -1


def test_analyze_game_builds_rows_for_the_selected_player(monkeypatch):
    game = chess.pgn.read_game(
        StringIO(
            '[White "Alice"]\n[Black "Bob"]\n[WhiteElo "1200"]\n'
            '[BlackElo "1300"]\n[Result "1-0"]\n\n'
            "1. e4 {[%clk 0:04:50]} e5 {[%clk 0:04:55]} "
            "2. Nf3 {[%clk 0:04:40]} *"
        )
    )
    before_first = {"pv": [chess.Move.from_uci("e2e4")]}
    before_second = {"pv": [chess.Move.from_uci("g1f3")]}
    analysis_results = iter([before_first, {}, before_second, {}])
    scores = iter([100, 80, 40, -100])
    monkeypatch.setattr(
        move_analysis,
        "analyze_position",
        lambda engine, board, depth: next(analysis_results),
    )
    monkeypatch.setattr(
        move_analysis,
        "score_for_player",
        lambda info, color: next(scores),
    )
    monkeypatch.setattr(move_analysis, "mate_for_player", lambda info, color: None)

    rows = analyze_game(object(), game, "alice", depth=8)

    assert len(rows) == 2
    assert rows[0]["opponent"] == "Bob"
    assert rows[0]["my_rating"] == "1200"
    assert rows[0]["move"] == "e4"
    assert rows[0]["best_move"] == "e4"
    assert rows[0]["played_best_move"] is True
    assert rows[0]["time_since_my_last_move"] == ""
    assert rows[1]["move"] == "Nf3"
    assert rows[1]["time_since_my_last_move"] == 10.0
    assert rows[1]["time_since_my_opponents_move"] == ""
    assert rows[1]["classification"] == "blunder"


def test_analyze_game_ignores_games_without_the_player():
    game = chess.pgn.Game()
    game.headers.update({"White": "Alice", "Black": "Bob"})

    assert analyze_game(object(), game, "Carol", depth=8) == []
