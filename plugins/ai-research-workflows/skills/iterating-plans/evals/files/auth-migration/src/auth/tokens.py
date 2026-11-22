"""Signed tokens that replace server-side sessions."""
import hashlib
import hmac


def sign(user_id, key):
    mac = hmac.new(key, str(user_id).encode(), hashlib.sha256).hexdigest()
    return f"{user_id}.{mac}"


def verify(token, key):
    user_id, _, mac = token.partition(".")
    expected = hmac.new(key, user_id.encode(), hashlib.sha256).hexdigest()
    return user_id if hmac.compare_digest(mac, expected) else None
