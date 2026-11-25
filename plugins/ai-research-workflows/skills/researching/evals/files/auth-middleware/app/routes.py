"""Routes; the profile and orders routes need a signed-in user."""
from app.middleware import require_user


@require_user
def profile(request):
    return {"status": 200, "name": request["user"]["name"]}


@require_user
def orders(request):
    return {"status": 200, "owner": request["user"]["id"], "orders": []}


def health(request):
    return {"status": 200}


ROUTES = {"/profile": profile, "/orders": orders, "/health": health}
