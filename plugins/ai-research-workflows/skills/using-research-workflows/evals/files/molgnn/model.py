"""A tiny message-passing model over molecular graphs."""
import random


class MPNN:
    def __init__(self, rounds=2, seed=0):
        rng = random.Random(seed)
        self.rounds = rounds
        self.w_self, self.w_nbr, self.w_out = (rng.uniform(-1, 1) for _ in range(3))

    def forward(self, atoms, bonds):
        h = list(atoms)
        for _ in range(self.rounds):
            nbr = [0.0] * len(h)
            for a, b in bonds:
                nbr[a] += h[b]
                nbr[b] += h[a]
            h = [max(0.0, self.w_self * x + self.w_nbr * m) for x, m in zip(h, nbr)]
        return self.w_out * sum(h) / len(h)
