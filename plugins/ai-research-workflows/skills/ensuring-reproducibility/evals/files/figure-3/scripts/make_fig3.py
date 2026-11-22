"""Draw Figure 3 (dose-response scatter) as figures/fig3.svg."""
import argparse
import csv
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    with open("data/fig3.csv", newline="", encoding="utf-8") as fh:
        rows = [(float(r["dose"]), float(r["response"])) for r in csv.DictReader(fh)]
    dots = []
    for dose, response in rows:
        x = 40 + dose * 30 + rng.uniform(-4, 4)  # jitter so overlapping doses stay visible
        y = 260 - response * 2
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3"/>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">' + "".join(dots) + "</svg>\n"
    Path("figures").mkdir(exist_ok=True)
    Path("figures/fig3.svg").write_text(svg, encoding="utf-8")
    print(f"wrote figures/fig3.svg ({len(rows)} points)")


if __name__ == "__main__":
    main()
