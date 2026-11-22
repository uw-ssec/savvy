import unittest

from src.cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestTTLCache(unittest.TestCase):
    def test_hit_before_expiry(self):
        clock = FakeClock()
        cache = TTLCache(ttl=10, clock=clock)
        cache.set("a", 1)
        clock.now = 9
        self.assertEqual(cache.get("a"), 1)

    def test_miss_after_expiry(self):
        clock = FakeClock()
        cache = TTLCache(ttl=10, clock=clock)
        cache.set("a", 1)
        clock.now = 10
        self.assertIsNone(cache.get("a"))

    def test_evicts_least_recently_used(self):
        cache = TTLCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)


if __name__ == "__main__":
    unittest.main()
