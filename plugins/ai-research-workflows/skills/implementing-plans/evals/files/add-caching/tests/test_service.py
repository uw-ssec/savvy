import unittest
from unittest import mock

from src import service


class TestGetStation(unittest.TestCase):
    def test_second_call_is_served_from_cache(self):
        with mock.patch.object(service, "slow_lookup", wraps=service.slow_lookup) as lookup:
            service.get_station("s-cache-test")
            service.get_station("s-cache-test")
        self.assertEqual(lookup.call_count, 1)


if __name__ == "__main__":
    unittest.main()
