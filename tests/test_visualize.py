import csv

from chess_analysis.visualize import browser_row, generate_html, move_squares


def analysis_row():
    return {
        "result": "win",
        "color": "White",
        "opponent": "Opponent",
        "time_since_my_last_move": "12",
        "time_spent": 12.0,
        "my_time_remaining": "88",
        "move_number": 1,
        "phase": "opening",
        "piece": "pawn",
        "move": "e4",
        "best_move": "e4",
        "classification": "good",
        "centipawn_loss": 0.0,
        "material_before": 0.0,
        "capture": False,
        "check": False,
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    }


def test_move_squares_and_browser_row_convert_a_move_for_javascript():
    row = analysis_row()

    assert move_squares(row, "move") == ("e2", "e4")
    browser = browser_row(row)

    assert browser["played_from"] == "e2"
    assert browser["played_to"] == "e4"
    assert browser["tags"]["phase"] == "opening"


def test_move_squares_returns_empty_coordinates_for_invalid_san():
    row = analysis_row()
    row["move"] = "not a move"

    assert move_squares(row, "move") == (None, None)


def test_generate_html_embeds_normalized_rows(tmp_path):
    filename = tmp_path / "analysis.csv"
    row = analysis_row()
    with filename.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)

    html = generate_html(filename, min_samples=1, limit=5)

    assert "Chess analysis explorer" in html
    assert '"played_from": "e2"' in html
    assert "__DATA__" not in html
