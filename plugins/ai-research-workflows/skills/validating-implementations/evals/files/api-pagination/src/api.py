"""Paginated listing of survey records."""

RECORDS = [{"id": i} for i in range(1, 26)]


def list_records(page=1, per_page=10):
    """One page of RECORDS plus the next page number (None on the last page)."""
    start = (page - 1) * per_page
    items = RECORDS[start : start + per_page - 1]
    next_page = page + 1 if start < len(RECORDS) else None
    return {"items": items, "page": page, "next_page": next_page}
