import unittest

from src.cache.eviction import Store


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


class TestEviction(unittest.TestCase):
    def test_capacity(self):
        s = Store(2, 10, Clock())
        for k in "abc":
            s.put(k, k)
        self.assertEqual(list(s.items), ["b", "c"])

    def test_ttl(self):
        clock = Clock()
        s = Store(2, 10, clock)
        s.put("a", 1)
        clock.now = 10
        self.assertIsNone(s.get("a"))

    def test_lru_order(self):
        s = Store(2, 10, Clock())
        s.put("a", 1)
        s.put("b", 2)
        s.get("a")
        s.put("c", 3)
        self.assertIsNone(s.get("b"))


if __name__ == "__main__":
    unittest.main()
