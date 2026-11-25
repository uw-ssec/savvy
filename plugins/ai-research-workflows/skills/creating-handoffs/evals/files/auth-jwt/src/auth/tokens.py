"""Signed session tokens (HMAC-SHA256 over a JSON payload)."""
import base64
import hashlib
import hmac
import json
import time


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def encode(payload, key):
    body = _b64(json.dumps(payload, sort_keys=True).encode())
    sig = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode(token, key, now=None):
    body, sig = token.split(".")
    expected = _b64(hmac.new(key, body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise ValueError("bad signature")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    if payload["exp"] <= (time.time() if now is None else now):
        raise ValueError("expired")
    return payload
