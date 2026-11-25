"""GET /export.csv: the records as CSV, one page at a time."""
import csv
import io

from src.api.records import page

DEFAULT_LIMIT = 100


def export_csv(offset=0, limit=DEFAULT_LIMIT):
    """Return (body, headers) for one page of the CSV export."""
    rows = page(offset, limit)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id", "site", "value"])
    writer.writeheader()
    writer.writerows(rows)
    headers = {"Content-Type": "text/csv"}
    if len(rows) == limit:
        headers["Link"] = f"offset={offset + limit}&limit={limit}"
    return buf.getvalue(), headers
