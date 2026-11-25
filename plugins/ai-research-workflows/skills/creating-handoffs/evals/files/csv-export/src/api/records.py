"""In-memory record store used by the API."""

RECORDS = [{"id": i, "site": f"site-{i % 3}", "value": i * 0.5} for i in range(1, 251)]


def page(offset, limit):
    return RECORDS[offset : offset + limit]
