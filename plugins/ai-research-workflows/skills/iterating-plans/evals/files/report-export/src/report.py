"""Monthly station report."""


def summarize(rows):
    """Per-station mean of `value`."""
    totals = {}
    for row in rows:
        totals.setdefault(row["station"], []).append(row["value"])
    return {station: sum(v) / len(v) for station, v in totals.items()}
