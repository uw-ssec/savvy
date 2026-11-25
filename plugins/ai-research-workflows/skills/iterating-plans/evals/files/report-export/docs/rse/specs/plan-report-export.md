# Plan: Export the monthly report

Status: approved.

## What We're NOT Doing

- PDF output.

## Phase 1: Summary table

### Changes

- [x] `summarize(rows)` in `src/report.py` returns per-station means

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] Means match the spreadsheet for March

## Phase 2: CSV export

### Changes

- [ ] Add `export_csv(summary, path)` to `src/report.py` writing `station,mean` rows sorted by station
- [ ] Add `--export PATH` to `scripts/monthly_report.py`

### Success Criteria

#### Automated Verification

- [ ] tests pass

#### Manual Verification

- [ ] works well

## Phase 3: Scheduled run

### Changes

- [ ] Run the export on the first of each month

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The April export lands in the shared folder
