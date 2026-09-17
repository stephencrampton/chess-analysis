"""Generate actionable, baseline-relative insights from move analysis CSV data."""

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MIN_SAMPLES = 30
DEFAULT_LIMIT = 5
MAX_REPORTED_LOSS = 1000
SERIOUS_CLASSIFICATIONS = {"mistake", "blunder"}


@dataclass
class Segment:
    """Aggregate metrics for one slice of moves."""

    name: str
    moves: int = 0
    serious_errors: int = 0
    blunders: int = 0
    centipawn_loss: float = 0.0

    def add(self, row):
        self.moves += 1
        if row["classification"] in SERIOUS_CLASSIFICATIONS:
            self.serious_errors += 1
        if row["classification"] == "blunder":
            self.blunders += 1
        self.centipawn_loss += min(row["centipawn_loss"], MAX_REPORTED_LOSS)

    @property
    def serious_error_rate(self):
        return self.serious_errors / self.moves if self.moves else 0.0

    @property
    def blunder_rate(self):
        return self.blunders / self.moves if self.moves else 0.0

    @property
    def average_centipawn_loss(self):
        return self.centipawn_loss / self.moves if self.moves else 0.0


@dataclass
class Insight:
    """A ranked recommendation backed by one segment."""

    segment: Segment
    baseline: Segment
    dimension: str
    score: float


def parse_float(value):
    """Return a CSV number or None for an empty/invalid value."""
    try:
        return float(value) if value != "" else None
    except (TypeError, ValueError):
        return None


def material_context(material):
    """Put a material balance into a coarse, actionable category."""
    if material > 1:
        return "ahead"
    if material < -1:
        return "behind"
    return "equal material"


def move_stage(move_number):
    """Group moves into stages that are easy to act on."""
    if move_number <= 10:
        return "moves 1-10"
    if move_number <= 30:
        return "moves 11-30"
    return "move 31 onward"


def segment_names(row):
    """Return the dimensions used to find recurring weaknesses."""
    names = {
        "phase": row["phase"],
        "piece": f"{row['piece']} moves",
        "color": row["color"],
        "material": f"{material_context(row['material_before'])}",
        "move stage": move_stage(row["move_number"]),
    }

    if row["capture"]:
        names["captures"] = "captures"
    if row["check"]:
        names["checks"] = "checks"

    if row["time_spent"] is not None:
        if row["time_spent"] < 10:
            names["time"] = "moves played in under 10 seconds"
        elif row["time_spent"] >= 30:
            names["time"] = "moves given at least 30 seconds"

    return names


def read_rows(filename):
    """Read and normalize rows from an analysis CSV."""
    with open(filename, newline="", encoding="utf-8") as csvfile:
        for raw_row in csv.DictReader(csvfile):
            centipawn_loss = parse_float(raw_row.get("centipawn_loss"))
            material_before = parse_float(raw_row.get("material_before"))
            move_number = parse_float(raw_row.get("move_number"))

            if (
                centipawn_loss is None
                or material_before is None
                or move_number is None
                or not raw_row.get("classification")
            ):
                continue

            yield {
                **raw_row,
                "centipawn_loss": centipawn_loss,
                "material_before": material_before,
                "move_number": int(move_number),
                "time_spent": parse_float(raw_row.get("time_since_my_last_move", "")),
                "capture": raw_row.get("capture", "").lower() == "true",
                "check": raw_row.get("check", "").lower() == "true",
            }


def collect_segments(rows):
    """Aggregate the overall baseline and every reportable dimension."""
    baseline = Segment("all moves")
    grouped = defaultdict(lambda: Segment(""))

    for row in rows:
        baseline.add(row)
        for dimension, name in segment_names(row).items():
            key = (dimension, name)
            grouped[key].name = name
            grouped[key].add(row)

    return baseline, grouped


def build_insights(baseline, grouped, min_samples):
    """Rank segments that are meaningfully worse than the baseline."""
    insights = []
    for (dimension, _), segment in grouped.items():
        if segment.moves < min_samples:
            continue

        error_excess = segment.serious_error_rate - baseline.serious_error_rate
        loss_ratio = (
            segment.average_centipawn_loss / baseline.average_centipawn_loss
            if baseline.average_centipawn_loss
            else 0
        )
        loss_excess = segment.average_centipawn_loss - baseline.average_centipawn_loss

        elevated_error_rate = error_excess >= 0.02
        elevated_loss = error_excess >= 0 and loss_ratio >= 1.25 and loss_excess >= 5
        if not elevated_error_rate and not elevated_loss:
            continue

        confidence = math.sqrt(segment.moves / baseline.moves)
        score = max(error_excess / 0.02, loss_excess / 5) * confidence
        insights.append(Insight(segment, baseline, dimension, score))

    return sorted(insights, key=lambda insight: insight.score, reverse=True)


def action_for(insight):
    """Turn a segment into a practical training suggestion."""
    name = insight.segment.name
    if insight.dimension == "phase":
        return f"study {name} positions and review your first decision after entering that phase"
    if insight.dimension == "piece":
        return f"review {name} and identify whether tactics or piece placement is driving the errors"
    if insight.dimension == "material":
        return f"practice converting {name} positions before playing more games"
    if insight.dimension == "time":
        return "review the position before moving and use a blunder check before committing"
    if insight.dimension == "captures":
        return "calculate the opponent's forcing reply before every capture"
    if insight.dimension == "checks":
        return "compare forcing checks with quieter candidate moves before committing"
    if insight.dimension == "move stage":
        return f"review {name} for recurring decisions and make a deliberate plan"
    return f"review games where you played as {name}"


def format_insight(number, insight):
    """Format one ranked insight for a human reader."""
    segment = insight.segment
    baseline = insight.baseline
    return (
        f"{number}. {segment.name}: {segment.serious_error_rate:.1%} serious errors "
        f"({segment.serious_errors}/{segment.moves}) vs "
        f"{baseline.serious_error_rate:.1%} overall; average loss "
        f"{segment.average_centipawn_loss:.1f} cp vs "
        f"{baseline.average_centipawn_loss:.1f} cp.\n"
        f"   Action: {action_for(insight)}."
    )


def format_report(baseline, insights, limit):
    """Format the complete actionable report."""
    if not baseline.moves:
        return "No usable move rows found in the analysis CSV."

    lines = [
        "Actionable chess analysis",
        f"Moves analyzed: {baseline.moves}",
        (
            f"Overall serious-error rate: {baseline.serious_error_rate:.1%} "
            f"({baseline.serious_errors} mistakes or blunders)"
        ),
        (
            f"Average centipawn loss (capped at {MAX_REPORTED_LOSS}): "
            f"{baseline.average_centipawn_loss:.1f}"
        ),
        "",
    ]

    if not insights:
        lines.append("No recurring weakness met the sample-size and effect thresholds.")
        return "\n".join(lines)

    lines.append("Focus areas")
    lines.extend(
        format_insight(number, insight)
        for number, insight in enumerate(insights[:limit], start=1)
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Summarize analysis CSV data into actionable focus areas."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        help="analysis CSV file (default: newest analysis_*.csv)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=DEFAULT_MIN_SAMPLES,
        help=f"minimum moves in a segment (default: {DEFAULT_MIN_SAMPLES})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"maximum focus areas to print (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--output",
        help="also write the report to a text file",
    )
    args = parser.parse_args()

    csv_file = args.csv_file
    if csv_file is None:
        candidates = sorted(
            Path.cwd().glob("analysis_*.csv"), key=lambda path: path.stat().st_mtime
        )
        if not candidates:
            parser.error("no analysis CSV found; pass a CSV filename")
        csv_file = str(candidates[-1])

    if args.min_samples < 1 or args.limit < 1:
        parser.error("--min-samples and --limit must be positive")

    baseline, grouped = collect_segments(read_rows(csv_file))
    report = format_report(
        baseline,
        build_insights(baseline, grouped, args.min_samples),
        args.limit,
    )
    print(report)

    if args.output:
        output = args.output
    else:
        output = None

    if output:
        Path(output).write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote {output}")


if __name__ == "__main__":
    main()
