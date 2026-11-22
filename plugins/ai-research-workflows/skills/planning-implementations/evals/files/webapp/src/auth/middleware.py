"""Attach the logged-in user to each request before the handler runs."""
from src.auth import sessions


def session_middleware(handler):
    def wrapped(request):
        sid = request.get("cookies", {}).get("sid")
        request["user"] = sessions.lookup(sid) if sid else None
        if request["user"] is None and request.get("requires_login", True):
            return {"status": 401, "body": "login required"}
        return handler(request)

    return wrapped
