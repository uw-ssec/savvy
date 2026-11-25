"""Retry transient load failures with capped exponential backoff."""
import time


class TransientError(Exception):
    pass


def with_retry(fn, attempts=4, base=0.5, cap=8.0, sleep=time.sleep):
    for attempt in range(attempts):
        try:
            return fn()
        except TransientError:
            if attempt == attempts - 1:
                raise
            sleep(min(cap, base * 2**attempt))
