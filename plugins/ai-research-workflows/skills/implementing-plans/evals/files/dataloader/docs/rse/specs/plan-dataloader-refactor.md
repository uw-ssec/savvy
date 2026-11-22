# Plan: Data-loader refactor

Status: approved.

## Overview

`src/loader.py` mixes CSV parsing and batching. Split them so each can be
tested on its own, then add a streaming reader for large files.

## Phase 1: Separate parsing from batching

### Changes

- [ ] Move `load_rows()` into a new `src/parsing.py`; `src/loader.py` imports it.
- [ ] Add `tests/test_parsing.py` covering a two-row CSV in a temporary file.

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Callers of `src.loader.load_rows` still work unchanged

## Phase 2: Streaming reader

### Changes

- [ ] Add `iter_rows(path)` to `src/parsing.py` that yields rows without reading the whole file.

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Memory stays flat when reading a 1 GB file
