import unittest

from src.ratelimit import TokenBucket


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestTokenBucket(unittest.TestCase):
    def test_allows_a_burst_up_to_capacity(self):
        bucket = TokenBucket(rate=1, capacity=3, clock=FakeClock())
        self.assertEqual([bucket.allow() for _ in range(4)], [True, True, True, False])

    def test_refills_over_time(self):
        clock = FakeClock()
        bucket = TokenBucket(rate=1, capacity=1, clock=clock)
        bucket.allow()
        clock.now = 1.0
        self.assertTrue(bucket.allow())


if __name__ == "__main__":
    unittest.main()
