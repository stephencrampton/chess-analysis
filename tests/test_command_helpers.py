from types import SimpleNamespace

import chess.pgn

import chess_analysis.analyze_games as analyze_module
import chess_analysis.download_games as download_module


def test_analyze_helpers_format_titles_and_manage_worker_engines(monkeypatch, capsys):
    game = chess.pgn.Game()
    game.headers.update(
        {
            "White": "Alice",
            "Black": "Bob",
            "WhiteElo": "1200",
            "BlackElo": "1300",
            "Result": "1-0",
        }
    )
    assert analyze_module.game_title(game) == "Alice* (1200) vs Bob (1300)"

    analyze_module.show_progress(1, 2, "Alice")
    analyze_module.clear_progress()
    assert "1/2" in capsys.readouterr().out

    engine = SimpleNamespace(quit=lambda: setattr(engine, "closed", True))
    analyze_module._worker_engine = engine
    analyze_module.close_worker_engine()
    assert engine.closed is True
    assert analyze_module._worker_engine is None

    opened = SimpleNamespace(quit=lambda: None)
    monkeypatch.setattr(analyze_module, "open_engine", lambda path: opened)
    analyze_module.initialize_worker("stockfish")
    assert analyze_module._worker_engine is opened

    expected = ["row"]
    monkeypatch.setattr(analyze_module, "analyze_game", lambda *args: expected)
    assert analyze_module.analyze_game_in_worker(("game", "Alice", 8)) == expected
    analyze_module.shutdown_worker()
    assert analyze_module._worker_engine is None


def test_download_games_fetches_months_and_reverses_pgn_order(tmp_path, monkeypatch):
    class FixedDate:
        @classmethod
        def now(cls, timezone):
            return cls()

        def date(self):
            return SimpleNamespace(year=2026, month=3)

    responses = [
        SimpleNamespace(
            status_code=200, text="March games", raise_for_status=lambda: None
        ),
        SimpleNamespace(status_code=404, text="", raise_for_status=lambda: None),
    ]
    requested_urls = []

    def get(url, **kwargs):
        requested_urls.append(url)
        return responses.pop(0)

    monkeypatch.setattr(download_module, "datetime", FixedDate)
    monkeypatch.setattr(download_module.requests, "get", get)
    output = tmp_path / "games.pgn"

    download_module.download_games("Alice", months=2, output=output)

    assert requested_urls == [
        "https://api.chess.com/pub/player/alice/games/2026/03/pgn",
        "https://api.chess.com/pub/player/alice/games/2026/02/pgn",
    ]
    assert output.read_text() == "March games"
