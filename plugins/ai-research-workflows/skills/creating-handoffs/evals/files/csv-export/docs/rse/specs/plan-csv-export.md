# Plan: CSV export endpoint

Status: approved.

## Phase 1: Export endpoint

- [ ] Add `export_csv()` in `src/api/export.py` returning one page of records as CSV

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

## Phase 2: Pagination

- [ ] Follow the next-page header until the last page; test a full walk of all 250 records

#### Automated Verification

- [ ] A test walks every page and gets each record exactly once
