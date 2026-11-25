"""Load molecules: atom features, bonds and the target, one per line."""
import csv


def load(path="data/molecules.csv"):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            atoms = [float(x) for x in row["atoms"].split()]
            bonds = [tuple(int(i) for i in pair.split("-")) for pair in row["bonds"].split()]
            out.append((atoms, bonds, float(row["target"]), row["split"]))
    return out
