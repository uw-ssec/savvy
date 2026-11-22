"""Background jobs that run in the same process as the API."""
from src.auth import sessions


def report_active_sessions():
    """Hourly metric; it can only see sessions created in this process."""
    return {"active_sessions": sessions.active_count()}
