---
name: ensuring-reproducibility
description: >-
  Use when a result, figure, or analysis must be reproducible by others or at
  a later date. Triggers: make this reproducible, capture provenance, pin the
  environment for this result, can't reproduce a result, numbers differ
  across runs or machines, a reviewer or journal asks for code and data
  availability, before reporting a number in a paper. Not for writing a
  lockfile (scientific-python-development:pixi-package-manager) or proving
  numbers correct (ai-research-workflows:hardening-research-code).
metadata:
  capability-network: read
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Ensuring Reproducibility

Record enough provenance to re-obtain a result exactly, then prove the record
works by reproducing it.

Default mode: Direct (protocol: `ai-research-workflows:using-research-workflows`).

## Purpose: when to use

A result must be re-runnable by others, or no longer reproduces. Not for
handing work to the next session (`ai-research-workflows:creating-handoffs`) or
proving numbers *correct* rather than *unchanged*
(`ai-research-workflows:hardening-research-code`).

## Iron Law: a record is not done until it has been reproduced

An unverified record is a hypothesis. Defer the clean-room run ONLY when a
fresh run is technically impossible (the hardware, proprietary data, or
licensed software is genuinely unavailable). **Being short on time is never a
valid reason.** If a full re-run is too long, run a *minimal* reproduction (a
smaller subset, fewer steps, one seed) in a clean environment: verify
something, never nothing. Until it reproduces, the record says `unverified`
and why, even if the user asked you to mark it reproducible.

## What the record captures

| Field | Record |
|---|---|
| Environment | interpreter version, OS, active lockfile (none: record installed versions and say so) |
| Code | commit hash (`git rev-parse HEAD`) and whether the tree was dirty |
| Hardware | GPU/accelerator, CUDA/driver version, thread counts |
| Data | path or URL plus version tag or content hash (`sha256`); retrieval date if remote |
| Seeds | every RNG's seed; if code reads seeds from config, pin that config file |
| Config | non-default flags, hyperparameters, config file contents |
| Commands | exact copy-pasteable commands, in order, plus the result values they produce |

Result no longer reproduces? Compare each row between the original run and
now; rows that differ, or were never recorded, are the diagnosis.

Read `references/provenance-record.md` when writing the record: full field
list, no-lockfile steps, tolerance format, skeleton.

**Where:** append a `## Reproducibility` section to the result's
`docs/rse/specs/experiment-<slug>.md` or `implement-<slug>.md` (or its legacy
`.agents/` copy); if neither exists, create `docs/rse/specs/reproducibility-<slug>.md` with that heading.

## Verify: clean-room reproduction

1. Fresh clone or copy and a new environment (keeps the original outputs intact).
2. Install from the lockfile or recorded versions only; no upgrades.
3. Run the recorded commands exactly.
4. Compare with the original result and write the outcome into the record. A
   mismatch is reported as a failure, never edited to match.

For nondeterministic outputs (GPU, parallelism), document a tolerance and the
hardware that produced it:

```text
Expected: 0.847 ± 0.003 (3 runs, seeds 42, 123, 999)
```

## Red flags: STOP, you're rationalizing the skip

| Thought | Reality |
|---|---|
| "The env is right here, it'll reproduce fine" | Not a clean room. Run it fresh. |
| "No time to spin up a clean environment" | Time is never a valid reason. Run a minimal one. |
| "Mark it reproducible now, verify after submission" | By then the number is in the paper. Verify first. |
| "It's deterministic, so it obviously reproduces" | Deps, hardware, unseeded RNGs drift. |
