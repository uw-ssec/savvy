"""Request handlers; each reads the user the middleware attached."""
from src.auth import sessions
from src.auth.middleware import session_middleware


def login(request):
    sid = sessions.create(request["form"]["user"])
    return {"status": 200, "cookies": {"sid": sid}}


@session_middleware
def profile(request):
    return {"status": 200, "body": {"user": request["user"]}}


@session_middleware
def logout(request):
    sessions.revoke(request["cookies"]["sid"])
    return {"status": 200}
