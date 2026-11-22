# Validating Implementations — Process Detail

The detail behind the Process steps in `SKILL.md`.

## Contents

- [Session context](#session-context)
- [Gather implementation evidence](#gather-implementation-evidence)
- [Read the plan](#read-the-plan)
- [Per-phase checks](#per-phase-checks)
- [Recording each check](#recording-each-check)
- [When a check fails](#when-a-check-fails)
- [Manual criteria](#manual-criteria)
- [After the report](#after-the-report)
- [Common mistakes](#common-mistakes)
- [Checklist before delivering](#checklist-before-delivering)

## Session context

**Same session (the implementation happened in this conversation):** you know
what was changed and which files were touched. Use that to find things, not as
evidence: re-run every check anyway.

**Fresh session (reviewing past work):** you have no memory of the decisions.
Reconstruct from git and the specs in `docs/rse/specs/`, and stick to what you
can observe: does the code match the plan, do the checks pass, are the
criteria met? Record each deviation as an observed fact; if its reason matters,
ask rather than invent one.

## Gather implementation evidence

See what was actually done before judging it:

```bash
git log --oneline -n 10
git diff <base>..HEAD --stat     # base: the branch point or the commit the plan started from
git rev-parse --short HEAD       # for the report's provenance line
```

Then run the project's test suite once as a baseline, using the command the
plan or the project documents (for example `pixi run pytest`).

## Read the plan

Read the entire plan (no partial reads) and, if it exists,
`docs/rse/specs/implement-<slug>.md`. For each phase note:

- which files should change;
- the success criteria, split into Automated and Manual Verification;
- the functionality that should exist;
- the tests that should be added (the plan's Testing Strategy).

## Per-phase checks

Work through every phase; run independent checks in parallel where you can,
and wait for all of them before writing the verdict.

- **Completion claims.** `- [x]` is claimed complete, `- [ ]` is not started
  or not finished. Neither is evidence.
- **Code changes.** Read the files the phase names. Are they changed as
  described? Does the implementation follow the plan's design and the
  codebase's patterns? Include schema, migration or config changes here when
  the plan has them.
- **Automated verification.** Run each command from the phase's Automated
  Verification section verbatim, with the plan's arguments. Don't substitute
  reading code for running a check.
- **Test coverage.** Find the tests added for the feature and confirm they
  cover the scenarios the Testing Strategy lists.
- **Reproducibility and correctness (research code).** If the work produces
  results, metrics or figures, confirm the seeds, data versions, environment
  and exact commands were captured (`ai-research-workflows:ensuring-reproducibility`)
  and that numerical results meet their stated criteria and tolerances
  (`ai-research-workflows:hardening-research-code`). Re-run to confirm the
  reported numbers reproduce. Long or costly re-runs: write to a separate
  output location so the original results stay intact.

## Recording each check

One line per command, with what you observed and what the plan expected:

```markdown
- ✅ `pixi run pytest` — 45 passed (expected 45)
- ❌ `pixi run pytest tests/test_spectrum.py` — 2 failed (expected 0)
- ✅ `pixi run mypy src/` — no errors
```

## When a check fails

1. Re-run it and read the full error output.
2. Find the failing code and cite it with a narrow `file:line`.
3. Classify the root cause: implementation bug, test bug, plan mismatch, or
   environment.
4. Record the command, the error, the root cause, the location and a
   recommendation with its priority (Critical / Important / Nice to Have).

A user or teammate calling a failure "flaky" doesn't change this. Re-run it
several times and check whether it touches the changed code. Until you have
shown it is unrelated, the overall status is Issues Found.

Keep going after a failure: run the remaining checks so the report shows the
full picture.

## Manual criteria

List each item from the plan's Manual Verification section under Manual
Testing Required with concrete steps and the expected outcome. If the user
confirmed one in this session, record it as user-confirmed; otherwise it is
still pending. Keep machine-verified results and human checks visibly apart.

## After the report

Validation reports; it does not repair. Don't edit the code, tests or data
under review. Offer to fix the findings after the report. If the plan itself
turns out to be wrong, point to `ai-research-workflows:iterating-plans`; if
phases are unfinished, to `ai-research-workflows:implementing-plans`.

## Common mistakes

- **Trusting a teammate's green report.** A chat message saying "all tests
  pass" is an unverified claim, exactly like a checkmark.
- **Trusting plan checkmarks** without running the checks.
- **Reporting "looks done"** without executing the automated verification.
- **Mixing automated and manual results**, or marking manual items done
  without the user's confirmation.
- **Speculating about intent** behind a deviation in a fresh session.
- **Stopping at the first failure.**
- **Pasting the status options** ("Ready | Issues Found | Incomplete") instead
  of choosing one.

## Checklist before delivering

- [ ] Read the entire plan (and the implementation summary, if any)
- [ ] Ran every automated verification command myself and recorded its output
- [ ] Investigated each failure to a root cause with a `file:line`
- [ ] Read the code for every phase, including phases marked complete
- [ ] Listed every deviation from the plan
- [ ] For research results: confirmed reproducibility capture and re-ran the
      reported numbers within tolerance
- [ ] Listed manual tests with steps and expected outcomes
- [ ] Grouped recommendations by severity
- [ ] Chose exactly one Overall Status
- [ ] Saved `docs/rse/specs/validation-<slug>.md` with provenance and
      References, and presented it inline
- [ ] Left the code under review unchanged
