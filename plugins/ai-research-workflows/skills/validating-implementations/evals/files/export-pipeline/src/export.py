"""Export result rows as CSV or JSON."""
import csv
import io
import json


def to_csv(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def to_json(rows):
    return json.dumps(rows, indent=2)


def export(rows, fmt, compress=False):
    """Serialise rows as `fmt` ("csv" or "json")."""
    if fmt == "csv":
        return to_csv(rows)
    if fmt == "json":
        return to_json(rows)
    raise ValueError(f"unknown format {fmt!r}")
