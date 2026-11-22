"""Write the weekly totals as CSV."""
import csv


def write_report(totals, out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "week", "total"])
        for (year, week), total in totals.items():
            w.writerow([year, week, f"{total:.2f}"])
