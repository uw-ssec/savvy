import unittest

from src.api import list_records


class TestPagination(unittest.TestCase):
    def test_first_page_has_per_page_items(self):
        self.assertEqual(len(list_records(1, 10)["items"]), 10)

    def test_last_page_holds_the_remainder(self):
        self.assertEqual([r["id"] for r in list_records(3, 10)["items"]], [21, 22, 23, 24, 25])

    def test_last_page_has_no_next_page(self):
        self.assertIsNone(list_records(3, 10)["next_page"])

    def test_first_page_points_to_page_two(self):
        self.assertEqual(list_records(1, 10)["next_page"], 2)


if __name__ == "__main__":
    unittest.main()
