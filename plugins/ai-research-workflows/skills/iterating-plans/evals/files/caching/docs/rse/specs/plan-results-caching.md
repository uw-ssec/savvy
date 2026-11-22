# Plan: Cache results in front of the database

Status: approved.

## Implementation Approach

Reads go through an in-memory cache in `src/store.py`. Writes are buffered and flushed to the database in batches of 500 (batched writes) to cut round-trips.

## What We're NOT Doing

- A distributed cache.

## Phase 1: Read-through cache

### Changes

- [x] `Store.get()` in `src/store.py` reads through the cache
- [x] Add `tests/test_store.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] Repeated reads in staging hit the database once

## Phase 2: Batched writes

### Changes

- [ ] Buffer `Store.put()` calls and flush every 500 writes with one `db.write_many()` call
- [ ] Flush the buffer on shutdown

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `python scripts/bench_writes.py` shows batched writes faster than one write per put

#### Manual Verification

- [ ] No writes are lost when the service is restarted mid-batch

## Phase 3: Metrics

### Changes

- [ ] Expose cache hit rate and buffered-write count

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Both metrics appear on the dashboard
