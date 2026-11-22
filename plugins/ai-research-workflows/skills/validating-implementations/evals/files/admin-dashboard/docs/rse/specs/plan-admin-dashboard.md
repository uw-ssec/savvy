# Plan: Admin dashboard

Status: approved.

## Phase 1: Static dashboard page

### Changes

- [x] Add `render_dashboard(stats)` to `src/dashboard.py`, one table row per statistic, values HTML-escaped
- [x] Add `tests/test_dashboard.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Open the rendered page in a browser and check the table is readable on a laptop screen
- [ ] Check the page with a screen reader announces the table headers
