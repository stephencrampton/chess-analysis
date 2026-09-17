from chess_analysis.download_games import previous_month
from chess_analysis.filenames import timestamped_filename
from chess_analysis.games import count_games, load_games


def test_previous_month_handles_january():
    assert previous_month(2026, 1) == (2025, 12)
    assert previous_month(2026, 9) == (2026, 8)


def test_filename_avoids_an_existing_timestamped_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "games_20260101_010203.pgn").touch()

    class FixedDate:
        @classmethod
        def now(cls, timezone):
            return cls()

        def strftime(self, pattern):
            return "20260101_010203"

    monkeypatch.setattr("chess_analysis.filenames.datetime", FixedDate)

    assert timestamped_filename("games", "pgn") == "games_20260101_010203_1.pgn"


def test_load_games_and_count_games_read_a_pgn_file(tmp_path):
    filename = tmp_path / "games.pgn"
    filename.write_text(
        '[White "Alice"]\n[Black "Bob"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
        '[White "Carol"]\n[Black "Dan"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
    )

    assert count_games(filename) == 2
    games = list(load_games(filename))
    assert [game.headers["White"] for game in games] == ["Alice", "Carol"]
