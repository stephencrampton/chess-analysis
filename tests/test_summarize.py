import csv

from chess_analysis.summarize import (
    Insight,
    Segment,
    action_for,
    build_insights,
    collect_segments,
    format_report,
    material_context,
    move_stage,
    parse_float,
    read_rows,
    segment_names,
)


def make_row(**changes):
    row = {
        "classification": "good",
        "centipawn_loss": "10",
        "material_before": "0",
        "move_number": "12",
        "phase": "middlegame",
        "piece": "knight",
        "color": "White",
        "capture": "true",
        "check": "false",
        "time_since_my_last_move": "35",
    }
    row.update(changes)
    return row


def test_read_rows_normalizes_values_and_skips_incomplete_rows(tmp_path):
    filename = tmp_path / "analysis.csv"
    with filename.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(make_row()))
        writer.writeheader()
        writer.writerow(make_row())
        writer.writerow(make_row(centipawn_loss="not a number"))

    rows = list(read_rows(filename))

    assert len(rows) == 1
    assert rows[0]["centipawn_loss"] == 10.0
    assert rows[0]["move_number"] == 12
    assert rows[0]["capture"] is True
    assert rows[0]["time_spent"] == 35.0


def test_collect_segments_and_build_insights_find_a_recurring_weakness():
    rows = [
        {
            "classification": "blunder",
            "centipawn_loss": 100,
            "material_before": 0,
            "move_number": 12,
            "phase": "middlegame",
            "piece": "knight",
            "color": "White",
            "capture": False,
            "check": False,
            "time_spent": None,
        }
        for _ in range(3)
    ] + [
        {
            "classification": "good",
            "centipawn_loss": 0,
            "material_before": 0,
            "move_number": 5,
            "phase": "opening",
            "piece": "pawn",
            "color": "White",
            "capture": False,
            "check": False,
            "time_spent": None,
        }
        for _ in range(3)
    ]
    baseline, grouped = collect_segments(rows)

    insights = build_insights(baseline, grouped, min_samples=2)

    assert baseline.moves == 6
    assert insights[0].dimension == "phase"
    assert insights[0].segment.name == "middlegame"
    assert action_for(insights[0]).startswith("study middlegame")


def test_format_report_explains_empty_and_successful_reports():
    empty = Segment("all moves")
    assert (
        format_report(empty, [], limit=5)
        == "No usable move rows found in the analysis CSV."
    )

    baseline = Segment("all moves")
    baseline.add({"classification": "mistake", "centipawn_loss": 60})
    report = format_report(baseline, [], limit=5)

    assert "Moves analyzed: 1" in report
    assert "No recurring weakness met" in report


def test_summary_helpers_cover_categories_and_optional_segments():
    assert parse_float("") is None
    assert parse_float("bad") is None
    assert parse_float("2.5") == 2.5
    assert material_context(2) == "ahead"
    assert material_context(-2) == "behind"
    assert material_context(0) == "equal material"
    assert move_stage(10) == "moves 1-10"
    assert move_stage(30) == "moves 11-30"
    assert move_stage(31) == "move 31 onward"

    row = {
        "phase": "opening",
        "piece": "pawn",
        "color": "White",
        "material_before": 2,
        "move_number": 31,
        "capture": True,
        "check": True,
        "time_spent": 5,
    }
    names = segment_names(row)
    assert names["material"] == "ahead"
    assert names["captures"] == "captures"
    assert names["checks"] == "checks"
    assert names["time"] == "moves played in under 10 seconds"

    row["time_spent"] = 30
    assert segment_names(row)["time"] == "moves given at least 30 seconds"


def test_action_and_report_format_cover_focus_area_output():
    baseline = Segment("all moves")
    segment = Segment("knight moves")
    for classification, loss in [("good", 0), ("blunder", 120)]:
        baseline.add({"classification": classification, "centipawn_loss": loss})
        segment.add({"classification": classification, "centipawn_loss": loss})
    insight = Insight(segment, baseline, "piece", 2.0)

    report = format_report(baseline, [insight], limit=1)

    assert "Focus areas" in report
    assert "knight moves" in report
    assert "tactics or piece placement" in report


def test_build_insights_can_rank_a_loss_based_signal():
    baseline = Segment("all moves")
    segment = Segment("slow moves")
    for _ in range(4):
        baseline.add({"classification": "good", "centipawn_loss": 10})
        segment.add({"classification": "good", "centipawn_loss": 30})

    insights = build_insights(baseline, {("time", "slow moves"): segment}, 4)

    assert len(insights) == 1
    assert insights[0].dimension == "time"
