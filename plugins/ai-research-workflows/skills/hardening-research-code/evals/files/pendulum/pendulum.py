"""Undamped pendulum theta'' = -(g/L) sin(theta), integrated with classical RK4."""
import math

G_OVER_L = 9.81


def deriv(state):
    theta, omega = state
    return (omega, -G_OVER_L * math.sin(theta))


def rk4_step(state, h):
    k1 = deriv(state)
    k2 = deriv(tuple(s + 0.5 * h * k for s, k in zip(state, k1)))
    k3 = deriv(tuple(s + 0.5 * h * k for s, k in zip(state, k2)))
    k4 = deriv(tuple(s + h * k for s, k in zip(state, k3)))
    return tuple(s + h / 6 * (a + 2 * b + 2 * c + d) for s, a, b, c, d in zip(state, k1, k2, k3, k4))


def simulate(theta0, omega0, h, steps):
    states = [(theta0, omega0)]
    for _ in range(steps):
        states.append(rk4_step(states[-1], h))
    return states


def energy(state):
    """Energy per unit mass and length squared: omega^2 / 2 + (g/L)(1 - cos theta)."""
    theta, omega = state
    return 0.5 * omega**2 + G_OVER_L * (1 - math.cos(theta))


if __name__ == "__main__":
    states = simulate(0.5, 0.0, 0.01, 10000)
    print(f"theta(100 s) = {states[-1][0]:.6f}, energy drift = {energy(states[-1]) - energy(states[0]):.3e}")
