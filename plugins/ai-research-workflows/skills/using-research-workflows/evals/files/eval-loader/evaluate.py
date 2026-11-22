"""Accuracy of the threshold model on the evaluation set."""
import csv

from src.loader import batches


def main(path="data/eval.csv", batch_size=32):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = [(float(r["score"]), int(r["label"])) for r in csv.DictReader(fh)]
    correct = total = 0
    for batch in batches(rows, batch_size):
        for score, label in batch:
            correct += int((score > 0.5) == bool(label))
            total += 1
    print(f"evaluated {total} of {len(rows)} examples, accuracy {correct / total:.4f}")


if __name__ == "__main__":
    main()
