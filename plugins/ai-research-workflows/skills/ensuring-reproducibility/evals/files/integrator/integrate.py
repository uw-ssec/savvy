"""Composite trapezoidal rule."""


def trapezoid(f, a, b, n=100):
    """Integral of f over [a, b] with n equal subintervals."""
    h = (b - a) / n
    return h * (0.5 * f(a) + sum(f(a + i * h) for i in range(1, n)) + 0.5 * f(b))
