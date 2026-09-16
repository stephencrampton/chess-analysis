#!/usr/bin/env python3

import argparse
import datetime
import requests


API = "https://api.chess.com/pub/player/{username}/games/{year}/{month:02d}/pgn"


def previous_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def download_games(username, months, output):
    today = datetime.date.today()
    year, month = today.year, today.month

    pgns = []

    for _ in range(months):
        url = API.format(
            username=username.lower(),
            year=year,
            month=month,
        )

        print(f"Fetching {year}-{month:02d}...")

        response = requests.get(
            url,
            headers={"User-Agent": "chess-game-analyzer/1.0"},
            timeout=30,
        )

        if response.status_code == 200 and response.text.strip():
            pgns.append(response.text)
        elif response.status_code != 404:
            response.raise_for_status()

        year, month = previous_month(year, month)

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n\n".join(reversed(pgns)))

    print(f"Wrote {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Download recent Chess.com games as PGN"
    )

    parser.add_argument("username")
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months to download (default: 6)",
    )
    parser.add_argument(
        "--output",
        default="games.pgn",
        help="Output PGN file (default: games.pgn)",
    )

    args = parser.parse_args()

    download_games(
        args.username,
        args.months,
        args.output,
    )


if __name__ == "__main__":
    main()
