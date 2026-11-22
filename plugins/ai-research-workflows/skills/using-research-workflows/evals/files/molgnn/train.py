"""Fit the output weight by gradient descent and report test RMSE."""
import argparse
import math

from data import load
from model import MPNN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=200)
    args = ap.parse_args()
    mols = load()
    model = MPNN(seed=args.seed)
    train = [m for m in mols if m[3] == "train"]
    for _ in range(args.epochs):
        for atoms, bonds, y, _split in train:
            pred = model.forward(atoms, bonds)
            model.w_out -= 0.01 * (pred - y) * pred / (model.w_out or 1e-9)
    test = [m for m in mols if m[3] == "test"]
    rmse = math.sqrt(sum((model.forward(a, b) - y) ** 2 for a, b, y, _ in test) / len(test))
    print(f"test RMSE {rmse:.3f}")


if __name__ == "__main__":
    main()
