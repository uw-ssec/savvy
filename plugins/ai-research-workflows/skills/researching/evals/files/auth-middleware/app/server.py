"""Dispatch a request through the middleware to its route."""
from app.middleware import attach_user
from app.routes import ROUTES


def handle(request):
    attach_user(request)
    return ROUTES[request["path"]](request)
