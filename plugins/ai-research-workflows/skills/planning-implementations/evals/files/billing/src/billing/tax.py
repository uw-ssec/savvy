"""Per-line tax calculation."""
from decimal import ROUND_HALF_UP, Decimal

RATES = {"standard": Decimal("0.20"), "reduced": Decimal("0.05"), "zero": Decimal("0")}


def line_tax(net, category, customer):
    if customer.get("tax_exempt"):
        return Decimal("0")
    rate = RATES[category]
    return (net * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
