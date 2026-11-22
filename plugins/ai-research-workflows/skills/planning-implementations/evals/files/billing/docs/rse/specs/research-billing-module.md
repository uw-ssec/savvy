# Research: billing module

Author: Priya. Status: complete.

## Question

How does an invoice get built today, and which tax cases does it get wrong?

## Invoice flow

1. `build_invoice()` (`src/billing/invoice.py:7`) walks the order lines.
2. For each line it computes `net = unit_price * qty` (`src/billing/invoice.py:11`).
3. It calls `line_tax()` (`src/billing/tax.py:7`) per line and sums the rounded
   per-line taxes into the invoice tax (`src/billing/invoice.py:15`).
4. The total is subtotal plus tax (`src/billing/invoice.py:16`). Nothing is
   persisted; the caller renders the dict.

## Tax calculation edge cases

- **Rounding per line.** Tax is rounded per line (`src/billing/tax.py:11`), so an
  invoice with many small lines can differ by several cents from tax computed on
  the subtotal. Finance wants rounding on the invoice total per rate.
- **Tax-exempt customers.** `tax_exempt` zeroes every line (`src/billing/tax.py:8`)
  but the invoice does not record why, which auditors require.
- **Unknown category.** An unknown `category` raises `KeyError`
  (`src/billing/tax.py:10`) and aborts the whole invoice.
- **Zero-rated vs exempt.** Zero-rated lines (`zero`) must still be listed with a
  0% rate on the invoice; exempt customers' lines must say "exempt". Today both
  show tax 0.00 with no rate.

## Tests

There are no tests for the billing module.
