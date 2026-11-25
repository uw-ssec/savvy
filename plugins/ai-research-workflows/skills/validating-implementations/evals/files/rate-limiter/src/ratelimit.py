"""Token-bucket rate limiting for the public API."""
import time


class TokenBucket:
    """Allow `rate` requests per second with bursts of up to `capacity`."""

    def __init__(self, rate, capacity, clock=time.monotonic):
        self.rate, self.capacity, self.clock = rate, capacity, clock
        self.tokens = float(capacity)
        self.updated = clock()

    def allow(self):
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
