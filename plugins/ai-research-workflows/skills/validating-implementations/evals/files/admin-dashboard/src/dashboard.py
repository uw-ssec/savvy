"""Render the admin dashboard as a static HTML page."""
from html import escape


def render_dashboard(stats):
    """HTML with one table row per (name, value) in stats."""
    rows = "".join(f"<tr><td>{escape(k)}</td><td>{escape(str(v))}</td></tr>" for k, v in stats.items())
    return f"<html><body><h1>Admin dashboard</h1><table>{rows}</table></body></html>"
