# Plan: Add caching to station lookups

Status: approved.

## Overview

`get_station()` (`src/service.py:8`) hits the slow catalogue query on every
call. Add a cache interface, then a shared cache backend.

## Phase 1: Cache interface

### Changes

- [ ] Add `src/cache.py` with a `Cache` protocol (`get`, `set`) and an in-process `DictCache`
- [ ] Use it in `get_station()` (`src/service.py:8`)

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] A repeated lookup in staging skips the catalogue query

## Phase 2: Shared memcached backend

### Changes

- [ ] Add `MemcachedCache` in `src/cache.py` using `pymemcache`, configured from `MEMCACHED_HOST`
- [ ] Select the backend with `CACHE_BACKEND=memcached`

### Success Criteria

#### Automated Verification

- [ ] Tests for `MemcachedCache` pass against a local memcached container

#### Manual Verification

- [ ] Two app instances share cached lookups
