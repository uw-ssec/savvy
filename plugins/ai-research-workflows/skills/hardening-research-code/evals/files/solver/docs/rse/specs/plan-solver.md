# Plan: Root solver for the equilibrium step

Status: approved.

## Phase 1: Bisection

### Changes

- [x] Add `bisect(f, lo, hi, tol, max_iter)` to `src/solver.py`, raising `ValueError` when the root is not bracketed
- [x] Add `tests/test_solver.py`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

## Phase 2: Newton fallback

### Changes

- [x] Add `newton(f, df, x0)` to `src/solver.py` for unbracketed starts
- [x] Test that `newton` converges on `x**2 - 2` from `x0 = 1`

### Success Criteria

#### Automated Verification

- [x] `python -m unittest discover -s tests -t .` passes

#### Manual Verification

- [ ] The equilibrium step converges for the three reference scenarios
