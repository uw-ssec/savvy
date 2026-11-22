import unittest

from src.api.export import export_csv


class TestExport(unittest.TestCase):
    def test_first_page_has_header_and_rows(self):
        body, headers = export_csv()
        lines = body.splitlines()
        self.assertEqual(lines[0], "id,site,value")
        self.assertEqual(len(lines), 101)
        self.assertEqual(headers["Content-Type"], "text/csv")


if __name__ == "__main__":
    unittest.main()
