---
name: validating-implementations
description: >-
  Use when an implementation is claimed complete and must be checked against
  its plan before a PR or merge. Triggers: validate the implementation, is it
  really complete or correct, verify it matches the plan, re-run the plan's
  checks, check before PR or merge, ready for PR, all tests pass so confirm
  it, success criteria, validation report. Not for unfinished work
  (ai-research-workflows:implementing-plans) or a plan that is itself wrong
  (ai-research-workflows:iterating-plans).
metadata:
  capability-network: none
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Validating Implementations

Check a finished implementation against every success criterion in its plan
and write a validation report.

## Iron Law: no verdict without fresh output you produced yourself

Plan checkmarks (`- [x]`), a teammate's "all 45 tests green, ready for PR", and
"looks done" are **claims, not evidence**. Before any verdict, re-run every
automated check yourself and read the actual code against each success
criterion. "Just confirm it's good" is a request to validate, not to
rubber-stamp. If you cannot run commands or read files here, say so and give
no verdict.

Default mode: Direct (`ai-research-workflows:using-research-workflows`).

## Quick reference

| Situation | Do |
|---|---|
| No plan path | Search `docs/rse/specs/{plan,implement}-*.md`, then legacy `.agents/`; ask if several match; stop if none. |
| Fresh session | Reconstruct from git and the specs; record deviations as observed facts. |

## Process

1. **Read the whole plan**, phase by phase.
2. **Run every Automated Verification command verbatim** (for example
   `pixi run pytest`). Run all of them, even after a failure, and record
   each actual output.
3. **Read the actual code** for each phase against its criteria. A `[x]`
   means "claimed complete", nothing more.
4. **Investigate every failure.** Re-run it, read the error, and name the root
   cause (implementation bug, test bug, plan mismatch, environment) with a
   narrow `file:line`. "Flaky" is a claim too. While any check fails, the
   status is **Issues Found**. For example:

   ```markdown
   - ❌ `pixi run pytest` — 2 failed (teammate reported all green). Root cause:
     implementation bug, window normalised twice at `src/pkg/spectrum.py:34`.
   ```
5. **Research results:** re-run what produced reported numbers and confirm
   they match within the stated tolerance.
6. **Manual criteria** go under **Manual Testing Required** with steps and the
   expected outcome. Never mark one passed unless the user confirmed it in
   this session.
7. **Report, don't fix.** Leave the code under review unchanged; offer fixes
   afterwards.

Read `references/validation-process.md` for evidence commands and failure
triage.

## The report

Write it to `docs/rse/specs/validation-<slug>.md` (slug from
`plan-<slug>.md`) **and** present it inline. A chat-only request still gets
the file, with its provenance and References: it is the verdict's record.
Only an explicit ban on writing files stops it; then say the verdict has no
record. The report:

- opens with provenance: plan, implementation summary, commit
  (`git rev-parse --short HEAD`) and date;
- gives exactly one **Overall Status**: Ready, Issues Found or Incomplete.
  Ready only if every check passed and every criterion is met;
- has `##` sections Implementation Status, Automated Verification Results,
  Code Review Findings, Manual Testing Required and Recommendations;
- ends with a `## References` section linking the plan and
  `implement-<slug>.md`.

Read `references/report-templates.md` when writing it.

## Red flags: you're about to rubber-stamp

| Thought | Reality |
|---|---|
| "They said all tests pass" | Unverified claim. Re-run it. |
| "Every box is `[x]`" | Read the actual code anyway. |
| "Those failures are flaky" | Re-run and find the root cause first. |
