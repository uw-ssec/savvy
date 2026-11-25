"""In-memory cache for catalogue lookups."""


class Cache:
    def __init__(self):
        self._data = {}
        self.hits = 0
        self.misses = 0

    def get(self, key):
        if key in self._data:
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return None

    def set(self, key, value):
        self._data[key] = value

    def invalidate(self, key):
        self._data.pop(key, None)
