# Hardening techniques

Part of `ai-research-workflows:hardening-research-code`. Read this when writing
the tests. `SKILL.md` holds the Iron Law, the criteria table, the tolerance rule
and the workflow; this file holds the detail for each kind of test.

This skill is the research-specific strategy layer: **what** to validate and
**why**. Defer pytest fixtures, parametrization, `numpy.testing` /
`torch.testing` assertion mechanics and CI configuration to the
`scientific-python-development:python-testing` skill. The same principles apply
to R, Julia, Fortran or any other runtime.

## Golden / reference tests

Compute expected outputs from a trusted source (an analytic formula, a reference
implementation or a published dataset) and assert that the code under test
matches them within tolerance. Store expected values and any input data in a
versioned file alongside the tests. Examples:

- A real sine wave whose frequency falls exactly on a DFT bin has one nonzero
  bin in a one-sided spectrum (two conjugate bins in the full DFT); every other
  bin is zero to within round-off. An off-bin frequency leaks into neighboring
  bins, so pick an on-bin test frequency.
- A fit recovers known parameters from synthetic data generated with them. This
  checks the fitting method; it does not verify the values the fit gives on the
  real data.
- An ODE integrator's error at a fixed end time, against an exact solution of
  the same equations (or a much finer-step run), shrinks at the method's order
  when the step is halved: about 16x per halving for RK4. A nonlinear pendulum
  compared with the small-angle (linear) solution keeps a linearization error
  that does not shrink with the step, so bound that error for the amplitude and
  time span used, or test the linear equations directly.

## Numerical-tolerance comparisons

Never use exact float equality. Use absolute or relative tolerances appropriate
to the domain:

```
# strategy-level pseudocode; defer mechanics to the python-testing skill
assert |result - expected| < atol + rtol * |expected|
```

Choosing the bound: start from the round-off the computation can accumulate,
roughly machine epsilon times the number of accumulating operations times the
magnitude of the quantities involved (`atol ≈ N · eps · scale`). For a sum,
`scale` is `Σ|xᵢ|`, not the size of the result: with cancellation the result
can be much smaller than the terms. This is a worst-case upper bound (the
classical bound for recursive summation is about `(N-1) · u · Σ|xᵢ|`, with unit
roundoff `u = eps/2`); typical error is far smaller, and pairwise or
compensated summation lowers the bound. For example, summing 10^6 float32
values (eps ≈ 1.2e-7) has a worst case near `0.06 · Σ|xᵢ|`, so an observed
change in the last digits after shuffling is expected; a change near the bound
signals a problem. Widen the bound only for a documented reason (iterative-solver
tolerance, truncation error of the method, stochastic variance). Use `rtol` for
values spanning orders of magnitude and `atol` for values near zero.

Document the justification next to the test: what physical or numerical argument
gives this bound? This applies to every bound, including `atol` values and
thresholds such as "the other bins are near zero", not only the main `rtol`. If the tolerance is tightened or loosened later, update the
justification.

**Never tune the tolerance to make a failing test pass.** A bound chosen to fit
the result is a silent correctness hole. If the observed error is above the
derived floor, either the method has a known error you can name and bound, or
there is a bug to investigate.

## Regression tests pinned to accepted outputs

Pin values only when those specific values can't reasonably be checked against
an analytic limit, reference implementation, published result or invariant. A
regression baseline is a fallback, not a substitute for verification. A check of
the method (for example, recovering known parameters from synthetic data) is
worth adding, but it doesn't verify the values the code gives on the real data,
so those stay `UNVERIFIED`. When pinning is the only option for a value:

1. Run the code on canonical inputs.
2. Check the outputs against whatever partial criteria you can: ranges, signs,
   invariants, expected trends.
3. Pin them. Future runs must stay within tolerance of that baseline.
4. **If the pinned values were not verified against an independent reference,
   label the baseline `UNVERIFIED`** in the test name or docstring and in the
   data file, so it is never mistaken for established-correct output. Tell
   whoever relies on it that it proves only that behavior hasn't changed.
5. Update the baseline deliberately, with a commit message explaining why the
   output changed.

## Stability checks

Perturb inputs, random seeds, data types (float32 vs float64), summation order
or batch sizes, and verify that outputs vary by a bounded amount. Compare
against a higher-precision computation where one is cheap (float64 or
`math.fsum` for a float32 sum). A result that changes dramatically under small
perturbations is not trustworthy, however close it is to a reference on the
nominal input. Report the numbers: how much the output moved under each
perturbation.

## Property / invariant checks

Assert structural properties that must hold regardless of the specific input
values: symmetry, monotonicity, conservation, idempotence or range bounds (for
example, probabilities are non-negative and sum to 1 within tolerance; a rotation
matrix has determinant 1; total energy is conserved). Check them over many
inputs, with a sweep or property-based testing, and add edge cases explicitly
(a single element, all-equal values, zeros, very large values). Cover the input
variations that commonly break numerical code: even and odd lengths, a nonzero
mean or offset, non-unit spacing or scale, and each dtype the code accepts
(float32 as well as float64). These catch whole classes of bugs that
value-comparison tests miss.

## When a correctness test fails on the current code

This is what hardening is for. Do not loosen the tolerance or re-pin to make it
pass. Report which criterion failed, with the expected and actual values, and record
it in the test's docstring (what the test caught, and whether the code was fixed
or is still failing) so the next reader knows the test guards a real defect. Fix
the code when the cause is clear and inside the code you were asked to harden,
and show the same test going from red to green. Otherwise leave the test failing
(or mark it as an expected failure with the reason) and ask the user how to
proceed. Either way, say whether results already produced by the code are
affected.

## Seeing each test fail

Perturb the expected value, the input, or temporarily the code (for example,
drop a factor of 2), run the test, watch it fail, then restore the original and
watch it pass. Check the diff afterwards so no perturbation is left behind.

## Reference data and provenance

Record each tolerance value and where reference or golden data lives. Version
reference data alongside the tests. For test-data provenance (content hashes,
retrieval dates, lockfile references), use
`ai-research-workflows:ensuring-reproducibility`. To confirm the hardened code
still meets its plan's success criteria, use
`ai-research-workflows:validating-implementations`.

## Common mistakes

- **Exact float equality.** `==` on floating-point results fails on trivially
  different hardware or library versions.
- **Tests with no stated criterion.** A test asserting a number without saying
  why that number is correct is uninterpretable when it fails. Name the
  analytic, reference or published source for each expected value.
- **Un-versioned reference data.** Golden outputs without a version tag, content
  hash or commit reference let a silent data change break tests with no
  explanation.
- **Testing implementation details.** Asserting internal intermediate values
  couples tests to the implementation. Test at the boundary where the
  correctness criterion applies.

## Completion checklist

- [ ] Correctness criteria are stated explicitly for each test
- [ ] Each baseline is verified against an independent reference, or labeled `UNVERIFIED`
- [ ] Each correctness test has been seen to fail when its criterion is violated
- [ ] All numerical comparisons use tolerances, not exact float equality
- [ ] Reference / golden data is versioned and its location is recorded
- [ ] Tests run in CI without manual intervention
- [ ] A failing test prints enough to diagnose the problem

## Limitations

Passing tests show that the stated criteria hold, not that the science is right.
The independent reference (an analytic limit, a synthetic case, an invariant) is
usually derived by the same agent that writes the tests, so a person should
review each stated criterion and its derivation before a baseline is relied on.
