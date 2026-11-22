"""Build an invoice from order lines."""
from decimal import Decimal

from src.billing.tax import line_tax


def build_invoice(customer, lines):
    """lines: [{"sku", "qty", "unit_price": Decimal, "category"}] -> invoice dict."""
    out, subtotal, tax_total = [], Decimal("0"), Decimal("0")
    for line in lines:
        net = line["unit_price"] * line["qty"]
        tax = line_tax(net, line["category"], customer)
        out.append({**line, "net": net, "tax": tax})
        subtotal += net
        tax_total += tax
    return {"customer": customer["id"], "lines": out, "subtotal": subtotal, "tax": tax_total, "total": subtotal + tax_total}
