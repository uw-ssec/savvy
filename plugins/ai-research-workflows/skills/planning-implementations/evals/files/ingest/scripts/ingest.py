"""Load station readings from a CSV into the readings database."""
import argparse
import csv
import sqlite3


def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS readings (station TEXT, ts TEXT, value REAL)")
    return db


def ingest(db, rows):
    count = 0
    for row in rows:
        db.execute("INSERT INTO readings VALUES (?, ?, ?)", (row["station"], row["ts"], float(row["value"])))
        count += 1
    db.execute("DELETE FROM readings WHERE value < 0")
    db.commit()
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--db", default="readings.db")
    args = ap.parse_args()
    with open(args.csv, newline="", encoding="utf-8") as fh:
        n = ingest(connect(args.db), csv.DictReader(fh))
    print(f"ingested {n} rows")


if __name__ == "__main__":
    main()
