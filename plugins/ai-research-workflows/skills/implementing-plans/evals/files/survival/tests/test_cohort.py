import unittest

from src.cohort import load_cohort, validate


class TestCohort(unittest.TestCase):
    def test_loads_every_patient(self):
        self.assertEqual(len(load_cohort("data/cohort_v3")), 10)

    def test_rejects_negative_time(self):
        with self.assertRaises(ValueError):
            validate([("p1", -1.0, 1)])

    def test_rejects_bad_event_flag(self):
        with self.assertRaises(ValueError):
            validate([("p1", 2.0, 3)])


if __name__ == "__main__":
    unittest.main()
