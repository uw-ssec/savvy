"""Entry point for the nightly pipeline."""
import csv

from pipeline.aggregate import weekly_totals
from pipeline.report import write_report


def main(path="data/readings.csv", out="weekly.csv"):
    with open(path, newline="", encoding="utf-8") as fh:
        readings = [(r["day"], float(r["value"])) for r in csv.DictReader(fh)]
    write_report(weekly_totals(readings), out)


if __name__ == "__main__":
    main()
