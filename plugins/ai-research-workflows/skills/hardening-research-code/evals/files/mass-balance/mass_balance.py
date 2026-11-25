"""Total mass from about a million float32 cell fluxes, accumulated in float32 as the model code does."""
import random
from array import array


def cell_fluxes(n=1_000_000, seed=7):
    """Synthetic fluxes standing in for one model step's output, stored as float32."""
    rng = random.Random(seed)
    return array("f", (rng.uniform(0.0, 2.0) * 10 ** rng.randint(-3, 3) for _ in range(n)))


def total_mass(fluxes):
    """Sum in a float32 accumulator, left to right."""
    acc = array("f", [0.0])
    for v in fluxes:
        acc[0] = acc[0] + v
    return acc[0]


if __name__ == "__main__":
    fluxes = cell_fluxes()
    print(f"total = {total_mass(fluxes):.6f}")
    shuffled = array("f", fluxes)
    random.Random(1).shuffle(shuffled)
    print(f"total after shuffle = {total_mass(shuffled):.6f}")
