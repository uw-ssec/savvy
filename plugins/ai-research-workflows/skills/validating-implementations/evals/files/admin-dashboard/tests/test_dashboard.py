import unittest

from src.dashboard import render_dashboard


class TestDashboard(unittest.TestCase):
    def test_one_row_per_stat(self):
        html = render_dashboard({"users": 3, "jobs": 7})
        self.assertEqual(html.count("<tr>"), 2)

    def test_values_are_escaped(self):
        self.assertIn("&lt;b&gt;", render_dashboard({"<b>": 1}))


if __name__ == "__main__":
    unittest.main()
