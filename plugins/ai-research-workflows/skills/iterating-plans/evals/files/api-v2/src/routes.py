"""Versioned API routes."""

ROUTES = {
    ("v1", "/records"): "list_records_v1",
    ("v2", "/records"): "list_records_v2",
}
