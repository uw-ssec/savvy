import unittest

from src.cache import Cache


class TestCache(unittest.TestCase):
    def test_get_after_set(self):
        cache = Cache()
        cache.set("a", 1)
        self.assertEqual(cache.get("a"), 1)

    def test_invalidate_removes_entry(self):
        cache = Cache()
        cache.set("a", 1)
        cache.invalidate("a")
        self.assertIsNone(cache.get("a"))


if __name__ == "__main__":
    unittest.main()
