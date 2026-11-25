"""Server-side session store (in-memory)."""
_SESSIONS = {}


def create(user):
    sid = f"s{len(_SESSIONS) + 1}"
    _SESSIONS[sid] = user
    return sid


def lookup(sid):
    return _SESSIONS.get(sid)
