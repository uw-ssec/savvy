"""Summary statistics for the measurement pipeline."""


def mean(xs):
    """Arithmetic mean of a non-empty sequence."""
    if not xs:
        raise ValueError("mean() needs at least one value")
    return sum(xs) / len(xs)


def variance(xs):
    """Sample variance (n - 1 denominator) of a sequence with at least two values."""
    if len(xs) < 2:
        raise ValueError("variance() needs at least two values")
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
