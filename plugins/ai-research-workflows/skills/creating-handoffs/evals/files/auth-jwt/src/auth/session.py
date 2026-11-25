"""Sessions backed by signed tokens instead of the old server-side dict."""
import time

from src.auth import tokens

ACCESS_TTL = 900


class SessionManager:
    def __init__(self, key):
        self.key = key
        self.revoked = set()

    def login(self, user_id, now=None):
        now = time.time() if now is None else now
        return tokens.encode({"sub": user_id, "exp": now + ACCESS_TTL, "iat": now}, self.key)

    def refresh(self, token, now=None):
        payload = tokens.decode(token, self.key, now)
        return self.login(payload["sub"], now)

    def logout(self, token):
        # TODO: record the token so validate() rejects it; only the set exists so far.
        pass

    def validate(self, token, now=None):
        payload = tokens.decode(token, self.key, now)
        if token in self.revoked:
            raise ValueError("revoked")
        return payload
