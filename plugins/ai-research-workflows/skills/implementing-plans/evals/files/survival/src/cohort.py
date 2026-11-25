"""Load and validate the survival cohort."""
import csv
from pathlib import Path


def load_cohort(directory):
    """Rows of <directory>/patients.csv as (id, time, event) tuples."""
    with open(Path(directory) / "patients.csv", newline="", encoding="utf-8") as fh:
        return [(r["id"], float(r["time"]), int(r["event"])) for r in csv.DictReader(fh)]


def validate(rows):
    """Raise ValueError on a negative follow-up time or an event flag other than 0/1."""
    for pid, time, event in rows:
        if time < 0:
            raise ValueError(f"{pid}: negative follow-up time")
        if event not in (0, 1):
            raise ValueError(f"{pid}: event must be 0 or 1")
    return rows
