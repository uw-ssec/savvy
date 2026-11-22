# Running the comparison

Detail for steps 1-6 of `running-experiments`. The Iron Law in SKILL.md still
governs: every approach you report on is built and run.

## Gathering context (step 1)

From the research and plan documents you read, identify the problem, its
constraints, the existing codebase patterns, and the integration points a
chosen approach must fit. Use them to pick candidates and set success criteria.

## Defining the approaches (step 2)

- State the question, what is being compared, and why the decision matters.
- Pick 2-3 approaches. Fewer than 2 is not an experiment; more than 3 makes the
  comparison hard to read.
- Approaches must differ in design, not in a setting. "JWT HS256 vs RS256" is a
  configuration difference; "stateless JWT vs server-side sessions" is an
  architectural one.
- Test one architectural variable at a time and hold everything else fixed.
- Write success criteria for each approach before running anything: how will
  you know it works (speed target, correctness, memory ceiling, fit with the
  existing code)?
- For each approach note pros, cons and a complexity rating (Low/Medium/High).

## Isolating prototypes (step 3)

- Prefer a scratch directory: `mkdir -p .experiments/<slug>`. It leaves the
  user's branch and package untouched.
- A branch (`git checkout -b experiment-<slug>`) moves the user's HEAD. Use it
  only on a clean working tree. With uncommitted changes, use the scratch
  directory rather than committing or stashing the user's work.
- Do not prototype inside the package (`src/`, `tests/`) behind a flag. The
  package changes only after a decision, as a planned implementation.
- Do not commit prototype code to the user's working branch. Leave the scratch
  directory or experiment branch in place after the run, state its path in the
  experiment document, and ask the user before deleting it.
- Install only the packages under comparison, from their official package
  index, pinned to an exact version, into an isolated environment where the
  project allows it. Record what you installed.

## Measuring (step 4)

Run real commands, for example:

```bash
python .experiments/<slug>/bench.py
pytest .experiments/<slug>/test_prototypes.py -v
```

For any performance claim:

- Use the same input for every approach; generate it once from a fixed seed or
  load the same file.
- Warm up once, then repeat each measurement several times (for example
  `timeit.repeat(..., repeat=7)`), and report the median with the spread
  (min-max or standard deviation), not a single number.
- Hold the environment constant: same machine, same interpreter, no other heavy
  jobs. Record Python and library versions and the hardware, per
  `ai-research-workflows:ensuring-reproducibility`.
- Check that each approach gives the correct result, not only a fast one: run
  tests, and compare its output against a reference implementation, reporting
  the largest difference.
- Run an integration check for each approach: call it the way the existing
  code would (same inputs, types and entry point) and record whether it fits.

## Recording observations (step 5)

For every approach, including the losers:

- What worked, what did not, and caveats (✅ / ❌ / ⚠️ in the template).
- Metrics: timings with spread, memory, error against the reference.
- Complexity: lines of code, new dependencies, integration points. Use
  `path/to/file.ext:lines` to show where a prototype would hook into existing
  code.
- Maintainability notes.
- Failed attempts and the reason they failed (an out-of-memory error at a given
  input size is a result). Never drop an approach from the report because it
  lost or crashed.

## Comparing and recommending (step 6)

Build a comparison matrix across performance, complexity, maintainability,
integration ease and test coverage, plus any criterion specific to the question
(accuracy, memory). Then fill the template's Recommendation section:
recommended approach, reasoning from specific measurements, why not each other
approach, caveats, and the conditions under which an alternative would be the
better choice.

## Common mistakes

- **Theorizing instead of running code**: describing what an approach "would
  probably do" produces opinions, not data.
- **Estimating one side**: building the favoured approach and assuming the
  other's result is not a head-to-head experiment.
- **Cherry-picking**: reporting only the winner's successes skews the
  comparison; record what was tried and why it was rejected for every approach.
- **Approaches that are not distinct**: two configuration variants collapse
  into a config choice, not an experiment.
- **Experimenting on a settled question**: if the codebase already uses a
  pattern consistently, follow it.
