"""Train and evaluate a nearest-centroid classifier on data/measurements.csv."""
import argparse
import csv
import json
import random


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, required=True)
    args = ap.parse_args()
    with open(args.config, encoding="utf-8") as fh:
        config = json.load(fh)
    with open(config["data"], newline="", encoding="utf-8") as fh:
        rows = [([float(r["x1"]), float(r["x2"])], r["label"]) for r in csv.DictReader(fh)]
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    n_test = int(len(rows) * config["test_fraction"])
    test, train = rows[:n_test], rows[n_test:]
    centroids = {}
    for label in sorted({y for _, y in train}):
        pts = [x for x, y in train if y == label]
        centroids[label] = [sum(c) / len(pts) for c in zip(*pts)]

    def predict(x):
        return min(centroids, key=lambda k: sum((a - b) ** 2 for a, b in zip(x, centroids[k])))

    accuracy = sum(predict(x) == y for x, y in test) / len(test)
    print(f"accuracy {accuracy:.3f}")


if __name__ == "__main__":
    main()
