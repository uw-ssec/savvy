import unittest

from src import middleware


class TestMiddleware(unittest.TestCase):
    def test_over_limit_returns_429(self):
        ok = lambda: {"status": 200, "headers": {}, "body": "ok"}
        statuses = [middleware.handle("client-a", ok, rate=0, capacity=2)["status"] for _ in range(3)]
        self.assertEqual(statuses, [200, 200, 429])


if __name__ == "__main__":
    unittest.main()
