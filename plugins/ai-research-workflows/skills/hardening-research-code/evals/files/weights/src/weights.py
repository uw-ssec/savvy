"""Normalise importance weights for the inference pipeline."""


def normalize_weights(x):
    """Non-negative weights summing to 1: negative inputs are clipped to 0, then divided by the total."""
    clipped = [max(0.0, float(v)) for v in x]
    total = sum(clipped)
    if total == 0:
        raise ValueError("all weights are zero or negative")
    return [v / total for v in clipped]
