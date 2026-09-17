"""Helpers for generating output filenames."""

from datetime import datetime, timezone
from pathlib import Path


def timestamped_filename(prefix, extension):
    """Return a unique UTC-timestamped filename in the current directory."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = Path(f"{prefix}_{timestamp}.{extension}")
    suffix = 1

    while output.exists():
        output = Path(f"{prefix}_{timestamp}_{suffix}.{extension}")
        suffix += 1

    return str(output)
