# Plan: API v2 rollout

Status: in progress.

## Overview

Ship the v2 API alongside v1, then move clients over.

## What We're NOT Doing

- Removing v1 in this rollout.

## Phase 1: Versioned routing

### Changes

- [x] Route `/v1/...` and `/v2/...` separately in `src/routes.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] v1 clients keep working against staging

## Phase 2: v2 endpoints

### Changes

- [x] `/v2/records` with cursor pagination
- [ ] `/v2/stations`
- [ ] `/v2/exports`

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The v2 endpoints return the same data as v1 for a sample of ids

## Phase 3: Webhook retry

### Changes

- [ ] Retry failed webhook deliveries with exponential backoff in `src/webhooks.py`
- [ ] Dead-letter deliveries after 5 attempts

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] A failing receiver gets 5 attempts, then the delivery is dead-lettered

## Phase 4: Client SDK

### Changes

- [ ] Add v2 methods to the Python client

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The SDK quick-start works against staging

## Phase 5: Admin dashboard

### Changes

- [ ] Add an admin page listing v1 and v2 traffic per client

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] An admin can see which clients still call v1
