"""Read measurement rows from CSV and group them into batches."""
import csv


def load_rows(path):
    """All rows of the CSV at path as dicts, with the value column as float."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["value"] = float(row["value"])
    return rows


def batches(rows, size):
    """Consecutive batches of `size` rows."""
    return [rows[i : i + size] for i in range(0, len(rows) - size + 1, size)]
