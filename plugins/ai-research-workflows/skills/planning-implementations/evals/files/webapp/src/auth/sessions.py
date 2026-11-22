"""Session store: a module-level dict, so sessions live in one process only."""
import secrets
import time

_SESSIONS = {}  # session id -> {"user": str, "expires": float}
TTL_SECONDS = 3600


def create(user):
    sid = secrets.token_hex(16)
    _SESSIONS[sid] = {"user": user, "expires": time.time() + TTL_SECONDS}
    return sid


def lookup(sid):
    entry = _SESSIONS.get(sid)
    if entry is None or entry["expires"] < time.time():
        _SESSIONS.pop(sid, None)
        return None
    return entry["user"]


def revoke(sid):
    _SESSIONS.pop(sid, None)


def active_count():
    return sum(1 for e in _SESSIONS.values() if e["expires"] >= time.time())
