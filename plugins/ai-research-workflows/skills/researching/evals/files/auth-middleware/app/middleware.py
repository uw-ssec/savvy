"""Request middleware: resolve the session cookie to a user."""
from app import sessions


def attach_user(request):
    """Set request["user"] from the session cookie, or None for anonymous requests."""
    sid = request.get("cookies", {}).get("sid")
    request["user"] = sessions.lookup(sid) if sid else None
    return request


def require_user(handler):
    def wrapped(request):
        if request.get("user") is None:
            return {"status": 401}
        return handler(request)

    return wrapped
