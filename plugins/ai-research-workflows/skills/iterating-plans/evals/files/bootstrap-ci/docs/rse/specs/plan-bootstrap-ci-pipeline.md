# Plan: Bootstrap a CI pipeline

## Overview

`src/stats.py` has no tests and nothing runs on pull requests. Add unit tests
first, then a CI workflow that runs them.

## What We're NOT Doing

- Coverage thresholds, linting or type checking.

## Phase 1: Unit tests for src/stats.py

### Changes

- [ ] Add an empty `tests/__init__.py` and `tests/test_stats.py` with `unittest` tests for `mean()` and `variance()`:
      a known small example for each, and the `ValueError` each raises on too few values.

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes from the project root

#### Manual Verification

- [ ] A reviewer confirms each test name says which behaviour it checks

## Phase 2: CI workflow

### Changes

- [ ] Add `.github/workflows/ci.yml` that runs the Phase 1 command on push and
      pull request with Python 3.12.

### Success Criteria

#### Automated Verification

- [ ] `python -c "import pathlib; assert pathlib.Path('.github/workflows/ci.yml').is_file()"` succeeds

#### Manual Verification

- [ ] The workflow runs green on a pull request on GitHub
