"""Client for the billing service."""
from svc.retrying import retry


def fetch_invoice(transport, invoice_id):
    return retry(lambda: transport.get(f"/invoices/{invoice_id}"), tries=5)
