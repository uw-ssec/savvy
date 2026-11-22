import math
import unittest

from src.solver import bisect


class TestBisect(unittest.TestCase):
    def test_finds_sqrt2(self):
        self.assertAlmostEqual(bisect(lambda x: x * x - 2, 0, 2), math.sqrt(2), places=8)

    def test_unbracketed_raises(self):
        with self.assertRaises(ValueError):
            bisect(lambda x: x * x + 1, 0, 1)


if __name__ == "__main__":
    unittest.main()
