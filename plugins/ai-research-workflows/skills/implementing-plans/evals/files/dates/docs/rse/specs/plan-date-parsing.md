# Plan: Accept day-first dates

Status: approved.

## Overview

Field sheets record dates as DD/MM/YYYY; `parse_date()` only accepts ISO dates.

## Phase 1: Day-first parsing

### Changes

- [ ] In `src/utils/dates.py`, extend `parse_date()` to accept `DD/MM/YYYY` as well as ISO dates
- [ ] Add `tests/test_dates.py` covering both formats and an invalid date

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] A sample field sheet imports with the right dates
