"""Eviction for the cache layer (Phase 2 of the plan, in progress)."""
from collections import OrderedDict


class Store:
    def __init__(self, maxsize, ttl, clock):
        self.maxsize, self.ttl, self.clock = maxsize, ttl, clock
        self.items = OrderedDict()

    def put(self, key, value):
        self.items[key] = (value, self.clock() + self.ttl)
        while len(self.items) > self.maxsize:
            self.items.popitem(last=False)

    def get(self, key):
        item = self.items.get(key)
        if item is None:
            return None
        # Not done yet: expiry is not checked and a hit does not refresh LRU order.
        return item[0]
