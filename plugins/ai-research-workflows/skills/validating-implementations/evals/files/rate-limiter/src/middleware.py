"""Apply a per-client token bucket to each request."""
from src.ratelimit import TokenBucket

_buckets = {}


def handle(client_id, handler, rate=5, capacity=10):
    """Call handler() if the client is under its limit; otherwise return a 429 response."""
    bucket = _buckets.setdefault(client_id, TokenBucket(rate, capacity))
    if not bucket.allow():
        return {"status": 429, "headers": {}, "body": "rate limit exceeded"}
    return handler()
