import json
import unittest

from src.export import export

ROWS = [{"site": "a", "value": 1}, {"site": "b", "value": 2}]


class TestExport(unittest.TestCase):
    def test_csv_has_header_and_rows(self):
        self.assertEqual(export(ROWS, "csv").splitlines(), ["site,value", "a,1", "b,2"])

    def test_json_round_trips(self):
        self.assertEqual(json.loads(export(ROWS, "json")), ROWS)

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            export(ROWS, "xml")

    def test_compress_flag_is_accepted(self):
        export(ROWS, "csv", compress=True)


if __name__ == "__main__":
    unittest.main()
