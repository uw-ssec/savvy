"""Load cleaned rows into the warehouse table."""
from src.etl.retry import with_retry


def load(rows, write_batch):
    return with_retry(lambda: write_batch(rows))
