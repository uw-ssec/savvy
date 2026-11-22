"""Fit y = a * exp(-b t) + c to data/decay.csv with Gauss-Newton least squares."""
import csv
import math


def load(path="data/decay.csv"):
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return [float(r["t"]) for r in rows], [float(r["y"]) for r in rows]


def model(p, t):
    a, b, c = p
    return a * math.exp(-b * t) + c


def jacobian_row(p, t):
    a, b, _ = p
    e = math.exp(-b * t)
    return [e, -a * t * e, 1.0]


def solve3(m, v):
    """Solve a 3x3 linear system by Gaussian elimination with partial pivoting."""
    m = [row[:] + [v[i]] for i, row in enumerate(m)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, 3):
            f = m[r][col] / m[col][col]
            m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    out = [0.0] * 3
    for r in (2, 1, 0):
        out[r] = (m[r][3] - sum(m[r][k] * out[k] for k in range(r + 1, 3))) / m[r][r]
    return out


def fit(ts, ys, p0=(2.0, 0.05, 0.0), iters=50):
    p = list(p0)
    for _ in range(iters):
        jtj = [[0.0] * 3 for _ in range(3)]
        jtr = [0.0] * 3
        for t, y in zip(ts, ys):
            j = jacobian_row(p, t)
            r = y - model(p, t)
            for i in range(3):
                jtr[i] += j[i] * r
                for k in range(3):
                    jtj[i][k] += j[i] * j[k]
        step = solve3(jtj, jtr)
        p = [pi + si for pi, si in zip(p, step)]
        if max(abs(s) for s in step) < 1e-12:
            break
    return p


if __name__ == "__main__":
    a, b, c = fit(*load())
    print(f"a = {a:.4f}, b = {b:.4f}, c = {c:.4f}")
