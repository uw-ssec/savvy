"""Server-side sessions keyed by an opaque session id (the format being retired)."""
import secrets

SESSIONS = {}


def create_session(user_id):
    sid = secrets.token_hex(16)
    SESSIONS[sid] = {"user_id": user_id}
    return sid


def lookup(sid):
    return SESSIONS.get(sid)
