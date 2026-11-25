"""A small LRU cache with a per-entry time-to-live."""
import time
from collections import OrderedDict


class TTLCache:
    def __init__(self, maxsize=128, ttl=60.0, clock=time.monotonic):
        self.maxsize, self.ttl, self.clock = maxsize, ttl, clock
        self._data = OrderedDict()

    def get(self, key, default=None):
        item = self._data.get(key)
        if item is None:
            return default
        value, expires = item
        if self.clock() >= expires:
            del self._data[key]
            return default
        self._data.move_to_end(key)
        return value

    def set(self, key, value):
        self._data[key] = (value, self.clock() + self.ttl)
        self._data.move_to_end(key)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)
