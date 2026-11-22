"""Median request latency from data/latency.csv."""
import csv
import statistics

with open("data/latency.csv", newline="", encoding="utf-8") as fh:
    values = [float(r["latency_ms"]) for r in csv.DictReader(fh)]
print(f"median latency {statistics.median(values):.0f} ms over {len(values)} requests")
