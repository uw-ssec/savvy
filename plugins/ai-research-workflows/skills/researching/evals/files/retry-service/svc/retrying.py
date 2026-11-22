"""Homegrown retry helper used by the service clients."""
import time


def retry(fn, tries=3, delay=1.0, exceptions=(ConnectionError, TimeoutError)):
    for i in range(tries):
        try:
            return fn()
        except exceptions:
            if i == tries - 1:
                raise
            time.sleep(delay * (i + 1))
