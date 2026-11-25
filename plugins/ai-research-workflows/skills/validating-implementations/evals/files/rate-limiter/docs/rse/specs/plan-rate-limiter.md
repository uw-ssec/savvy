# Plan: Rate limiting for the public API

Status: approved.

## Phase 1: Token bucket

### Changes

- [x] Add `TokenBucket` to `src/ratelimit.py` with an injectable clock
- [x] Add `tests/test_ratelimit.py` covering a burst and refill

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

## Phase 2: Per-client middleware

### Changes

- [x] Add `handle()` to `src/middleware.py` keeping one bucket per client id
- [x] Over-limit requests get status 429 and a `Retry-After` header giving the seconds until a token is free
- [x] Add `tests/test_middleware.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] A client sending 20 requests a second sees 429s with `Retry-After` in the staging logs
