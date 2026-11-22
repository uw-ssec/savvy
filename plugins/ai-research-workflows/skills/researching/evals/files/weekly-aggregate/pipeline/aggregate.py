"""Roll daily readings up into weekly totals."""
from collections import defaultdict
from datetime import date


def weekly_totals(readings):
    """Sum (day, value) readings per ISO (year, week)."""
    totals = defaultdict(float)
    for day, value in readings:
        year, week, _ = date.fromisoformat(day).isocalendar()
        totals[(year, week)] += value
    return dict(sorted(totals.items()))
