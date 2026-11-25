"""Client for the inventory service, with its own inline retry loop."""
import time


def reserve(transport, sku, qty):
    for attempt in range(4):
        try:
            return transport.post("/reservations", {"sku": sku, "qty": qty})
        except TimeoutError:
            time.sleep(0.2 * 2**attempt)
    raise TimeoutError(f"reserve {sku} failed after 4 attempts")
