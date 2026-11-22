---
name: hardening-research-code
description: >-
  Use when research or scientific code must be shown correct before its numbers
  are relied on, as in a paper. Triggers: harden this code, is this numerically
  correct, which version is right after a refactor, NaN or drift in float32,
  golden test, regression baseline, known analytic result, tolerance, float
  equality, numerical stability. Not for capturing provenance (use
  ensuring-reproducibility) or pytest setup (use python-testing).
metadata:
  capability-network: none
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Hardening Research Code

Make research code trustworthy: state what "correct" means, test it, and show
each test can fail. Default mode: Direct (protocol:
`ai-research-workflows:using-research-workflows`). Not for provenance
(`ai-research-workflows:ensuring-reproducibility`), plan checks
(`ai-research-workflows:validating-implementations`) or pytest mechanics
(`scientific-python-development:python-testing`).

## Iron Law: a regression baseline is not a correctness check

Pinned outputs prove only that behavior hasn't changed. Before pinning, check
whether an analytic, reference, published or invariant criterion (table below)
is reasonably derivable; test against it first. Label every pinned value not
checked against an independent reference `UNVERIFIED`, in the test and its data
file, and tell the user it shows no change, not correctness. Recovering known
parameters from synthetic data checks the method, not the pinned values.

## Quick Reference: correctness criteria

| Criterion | Example | Test shape |
|---|---|---|
| Analytic / closed form | on-bin sine: one nonzero one-sided bin | exact expected value |
| Reference implementation | numpy, scipy, astropy | same input, both outputs |
| Published result | a paper's table | reproduce within its stated error |
| Invariant / property | Parseval; weights ≥ 0, sum to 1 | many inputs plus edge cases |
| Stability | shuffled order, float32 vs float64 | bounded, numbers reported |
| Regression (fallback) | current outputs | pinned, `UNVERIFIED` unless verified |

## Tolerances

Never use exact float equality:

```python
assert abs(result - expected) <= atol + rtol * abs(expected)
```

Derive the bound from the numerics, starting at `atol ≈ N · eps · scale` (N
accumulating operations; for a sum, scale is `Σ|xᵢ|`), and widen it only for a
documented reason (solver tolerance, truncation error, stochastic variance).
Justify every bound in the test, including `atol` and near-zero thresholds.
**Never tune a tolerance to make a failing test pass.**

## Workflow

1. **Pick criteria**; state each in its test's docstring.
2. **Write one small test per criterion**, on observable outputs, across
   inputs that break numerics (even and odd sizes, float32, edge cases). Read
   `references/techniques.md` first.
3. **Run, then see each test fail.** Perturb the expected value or input, watch
   it go red, restore, watch it go green. A test never seen to fail proves
   nothing.
4. **A test failing on the current code is a finding**, not a test to loosen.
   Report criterion, expected and actual values, and note the defect in the
   test's docstring. Fix the code only when the cause is clear and in scope;
   otherwise leave it failing and ask.
5. **Report** tolerances, reference-data location, pass/fail, seen-to-fail
   evidence, perturbation numbers and `UNVERIFIED` baselines.

## Red flags: STOP, you're locking in a wrong result

| Thought | Reality |
|---|---|
| "Looks plausible, I'll pin it" | Check a reference, or label it `UNVERIFIED`. |
| "It's been right for years" | Untested isn't verified. |
| "`==` is fine, same machine" | CI and the next person aren't. |
| "Widen rtol so CI passes" | A bound fitted to the result hides the bug. Derive it. |
