# Workflow Patterns

Right-size the chain to the task. These are the menu, not a mandate to run all.
Skill names are short for `ai-research-workflows:<name>`.

## Common workflow patterns

### Full workflow (complex architectural change)

`researching` → `planning-implementations` → `running-experiments` →
`iterating-plans` → `implementing-plans` → `validating-implementations`

### Simple feature addition

`researching` → `planning-implementations` → `implementing-plans`

### Rapid iteration

`planning-implementations` → `iterating-plans` → `iterating-plans` →
`implementing-plans`

### Research-only / investigation

`researching` → `researching` (follow-up) — use docs for future planning.

### Research-first (unknown problem space)

`researching` → `planning-implementations`

## Skill priority & sequencing

Process-shaping skills come before execution: understand before you plan, plan
before you build, verify after.

1. **Understand first** — don't write or modify code until you've engaged
   `researching`; for anything non-trivial, then `planning-implementations`.
2. **Build second** — `implementing-plans` executes an approved plan.
3. **Verify last** — `validating-implementations`, plus `ensuring-reproducibility`
   / `hardening-research-code` whenever a result will be reported or relied on.

## Red flags — STOP, you're rationalizing

These thoughts mean you are about to skip a skill you should invoke:

| Thought | Reality |
|---|---|
| "I'll just tweak the code real quick" | Code changes need understanding first → `researching` then `planning-implementations`. |
| "I already know how this codebase works" | Memory drifts; the code is ground truth. Trace it with `researching`. |
| "5 minutes — don't overthink it" | Right-size the skill, don't skip it. A 90-second read still beats a stale-cache bug. |
| "This change is too small for a plan" | Small multi-file / network / state changes break callers. Plan it. |
| "It's just an experiment, no rigor needed" | Experiments drive design decisions → `running-experiments`; record failures too. |
| "The result obviously reproduces" | Unverified provenance is a hypothesis → `ensuring-reproducibility`. |
| "I'll capture provenance / harden it later" | Later never comes. Do it when the result is produced. |

## Common mistakes

- **Skipping the workflow because the task "looks small"** — the most common and
  most expensive mistake. Right-size the skill (a scoped `researching` pass, a
  short plan), but never skip skill-invocation entirely for a code change or a
  research investigation.
- **Forcing the *full* chain when one skill suffices** — the opposite error:
  running research → plan → experiment → implement → validate for a trivial change
  wastes time. Pick the minimal matching skill from the decision tree. This is
  about right-sizing, never about reaching zero skills.
- **Not picking an interaction mode** — every workflow skill defaults to a mode,
  but failing to confirm the right mode leads to unnecessary interruptions
  (Collaborative when Direct is wanted) or unreviewed decisions (Direct when
  Collaborative is needed).
- **Keeping a skill that doesn't fit** — if an invoked skill turns out not to
  fit, drop it. But check first: invoke, then decide.
- **Treating this skill as a substitute for the specialist skills** — this
  meta-skill routes and compels; the actual work happens in the individual
  skills. Invoke the right specialist skill rather than asking this one to execute.
