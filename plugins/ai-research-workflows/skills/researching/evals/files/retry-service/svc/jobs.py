"""Nightly job that reconciles invoices against reservations."""
from svc.billing_client import fetch_invoice
from svc.inventory_client import reserve


def reconcile(transport, invoice_ids):
    for invoice_id in invoice_ids:
        invoice = fetch_invoice(transport, invoice_id)
        for line in invoice["lines"]:
            reserve(transport, line["sku"], line["qty"])
