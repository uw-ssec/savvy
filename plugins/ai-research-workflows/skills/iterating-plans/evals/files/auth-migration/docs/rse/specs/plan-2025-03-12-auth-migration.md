# Plan: Migrate authentication from sessions to signed tokens

Status: approved.

## Overview

Replace the server-side sessions in `src/auth/session.py` with the signed tokens in `src/auth/tokens.py`.

## What We're NOT Doing

- Single sign-on or third-party identity providers.

## Phase 1: Token signing

### Changes

- [x] Add `sign()` and `verify()` to `src/auth/tokens.py`
- [x] Add `tests/test_tokens.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [x] A token signed in staging verifies in staging

## Phase 2: Issue tokens at login

### Changes

- [ ] Login returns a token from `sign()` instead of calling `create_session()`
- [ ] Requests carrying a token are authenticated with `verify()`

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Logging in through the web client yields a token

## Phase 3: Remove server-side sessions

### Changes

- [ ] Delete `src/auth/session.py` and its callers

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `grep -rn create_session src/` finds nothing

#### Manual Verification

- [ ] No active user is logged out by the release

## Phase 4: Clean up

### Changes

- [ ] Remove the session store configuration

### Success Criteria

#### Automated Verification

- [ ] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] Ops confirm the session store can be decommissioned
