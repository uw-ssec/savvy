# Plan: Cache layer for catalogue lookups

Status: approved.

## Phase 1: Basic cache

### Changes

- [x] Add `Cache` with `get()` and `set()` to `src/cache.py`
- [x] Add `tests/test_cache.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

## Phase 2: Invalidation and statistics

### Changes

- [x] Add `Cache.invalidate(key)`
- [ ] Add `Cache.hit_rate()` returning hits / (hits + misses), or 0.0 before any lookup
- [ ] Add `tests/test_stats.py` covering `hit_rate()` before and after lookups

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The hit rate shows up on the service status page
