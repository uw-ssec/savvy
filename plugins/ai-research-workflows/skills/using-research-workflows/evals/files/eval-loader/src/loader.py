"""Batch the evaluation set."""


def batches(items, batch_size):
    """Split items into batches of batch_size for evaluation."""
    n_full = len(items) // batch_size
    return [items[i * batch_size : (i + 1) * batch_size] for i in range(n_full)]
