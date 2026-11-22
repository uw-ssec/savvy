# Plan: Survival analysis for cohort v3

Status: approved.

## Overview

Estimate survival for the patients in `data/cohort_v3/patients.csv`
(`id,time,event`, time in months, event 1 = death, 0 = censored).

## Phase 1: Load the cohort

### Changes

- [x] Add `load_cohort()` to `src/cohort.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] Row count matches the cohort export (10 patients)

## Phase 2: Validate the cohort

### Changes

- [x] Add `validate()` to `src/cohort.py` rejecting negative times and bad event flags
- [x] Add `tests/test_cohort.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] Validation errors name the offending patient id

## Phase 3: Kaplan-Meier estimator

### Changes

- [ ] Add `km_estimate(times, events)` to a new `src/survival.py`, returning a list of
      `(time, survival)` pairs at each distinct event time
- [ ] Add `tests/test_survival.py` checking `km_estimate` against a hand-computed
      three-patient example

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The curve for `data/cohort_v3` matches the clinician's hand-drawn estimate

## Phase 4: Median survival report

### Changes

- [ ] Add `scripts/report.py` printing the median survival time for `data/cohort_v3`

### Success Criteria

#### Automated Verification

- [ ] `python scripts/report.py` prints a median survival time in months

#### Manual Verification

- [ ] The median agrees with the value in the clinical summary
