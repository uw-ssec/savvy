"""Weighted posterior mean, the step the paper reports."""
from src.weights import normalize_weights


def weighted_mean(samples, raw_weights):
    w = normalize_weights(raw_weights)
    return sum(s * wi for s, wi in zip(samples, w))
