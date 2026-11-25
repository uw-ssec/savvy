"""F1 of the positive class on the validation split predictions."""
import csv

with open("data/val_predictions.csv", newline="", encoding="utf-8") as fh:
    rows = [(r["label"], r["prediction"]) for r in csv.DictReader(fh)]
tp = sum(y == p == "1" for y, p in rows)
fp = sum(y == "0" and p == "1" for y, p in rows)
fn = sum(y == "1" and p == "0" for y, p in rows)
precision, recall = tp / (tp + fp), tp / (tp + fn)
print(f"validation F1 {2 * precision * recall / (precision + recall):.2f}")
