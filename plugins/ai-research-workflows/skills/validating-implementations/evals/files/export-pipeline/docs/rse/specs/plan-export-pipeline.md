# Plan: Export pipeline

Status: approved.

## Phase 1: CSV and JSON export

### Changes

- [x] Add `export(rows, fmt)` to `src/export.py` supporting `csv` and `json`
- [x] Unknown formats raise `ValueError`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

## Phase 2: Compressed output

### Changes

- [x] `export(..., compress=True)` returns gzip-compressed bytes of the serialised output
- [x] Add a test that decompresses the output and checks it matches the uncompressed export

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] A compressed export opens in the analysts' spreadsheet tool after unzipping
