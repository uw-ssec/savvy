# Plan: Cache layer

Status: approved.

## Phase 1: Store with capacity limit

- [x] Add `Store` in `src/cache/eviction.py` with `put()`/`get()` and a size limit
- [x] Add `tests/test_eviction.py::test_capacity`

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

## Phase 2: TTL and LRU eviction

- [ ] Expire entries after `ttl` seconds (`test_ttl`)
- [ ] Refresh recency on a hit so eviction is least-recently-used (`test_lru_order`)

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Hit rate on the staging replay is above 80%
