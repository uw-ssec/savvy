# Plan: Add caching to station lookups

Status: approved.

## Overview

`get_station()` hits the slow catalogue query on every call. Put an LRU cache
with a time-to-live in front of it.

## Phase 1: TTL cache

### Changes

- [x] Add `TTLCache` to `src/cache.py` (LRU eviction, per-entry TTL, injectable clock)
- [x] Add `tests/test_cache.py` covering a hit, expiry and LRU eviction

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] The TTL and size defaults are agreed with the data team

## Phase 2: Cache station lookups

### Changes

- [x] Wrap `slow_lookup()` in `src/service.py` with a module-level `TTLCache` (256 entries, 300 s)
- [x] Add `tests/test_service.py` showing a repeated lookup is served from the cache

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] A repeated lookup in the staging app returns without a catalogue query
