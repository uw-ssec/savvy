---
name: implementing-plans
description: >-
  Use when an approved implementation plan (a docs/rse/specs/plan-*.md file) is
  ready to build, or a partly built plan needs resuming. Triggers: implement the
  plan, execute the plan, run the plan, start building, the plan is approved,
  go build it, start phase 1, continue or resume implementation. Not for
  designing a plan (planning-implementations), changing one (iterating-plans), or checking
  finished work against one (validating-implementations).
metadata:
  capability-network: none
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Implementing Plans

Build an approved plan one phase at a time, verifying each phase and pausing
for the human before the next. Default mode: **Direct** (protocol:
`ai-research-workflows:using-research-workflows`).

**Not this skill:** no plan → `ai-research-workflows:planning-implementations`;
plan needs changes → `ai-research-workflows:iterating-plans`; checking finished
work → `ai-research-workflows:validating-implementations`.

## Hard gates

1. **Read and review before any code.** Read the whole plan and every file it
   names. Raise concerns and missing prerequisites (data, versions, seeds), or
   say it looks sound.
2. **Check the branch.** Never write code on `main`/`master` without explicit
   consent, in any mode: create a feature branch and say so, or ask.

   ```bash
   git branch --show-current   # main/master → git switch -c feature/<slug>
   ```

3. **Stop on a mismatch.** If the plan can't be followed as written (something
   it says exists isn't there or differs; a prerequisite is missing), present
   the mismatch report (expected, found, why it matters, options) and ask "How
   should I proceed?" Never adapt first and record the deviation later.
4. **Verify each phase** with the plan's automated checks; fix failures first.
5. **Pause for manual verification** after each phase and wait for the user.
   Never tick a manual item the user hasn't confirmed.

## Workflow

1. **Load and review** (gates 1–2); note existing `- [x]`; one task per phase.
2. **Implement one phase**, following existing patterns; tick each task
   `- [x]` when done; commit only at the plan's commit steps.
3. **Verify** (gate 4), reporting each command's result; **pause** (gate 5).
4. **Repeat** 2–3 per phase.
5. **Finish:** run the finish checklist in `references/workflow.md`, write
   `docs/rse/specs/implement-<slug>.md`, route to `ai-research-workflows:validating-implementations`.

## Quick reference

| Situation | Action |
|---|---|
| "Do phases 1–3" / "don't stop between phases" | Checks after each phase; one manual pause at the end; manual items stay unticked |
| Plan already has `- [x]` | Trust it; start at the first unchecked item |
| Only a line number or local name drifted | Adapt; record it as a deviation |
| Unsure whether it's a mismatch | Treat it as one |
| Phase produced a result | Capture provenance (`ai-research-workflows:ensuring-reproducibility`) |

## Red flags

| Thought | Reality |
|---|---|
| "You already approved the full plan, so I move straight into Phase 2" | Plan approval isn't phase sign-off. Pause. |
| "The plan is stale, not wrong in intent; I'll apply its intent and record the deviation" | That's a mismatch. Report and wait. |
| "I'll decide whether the deviation is small enough to proceed on my own" | Only incidental drift is. |
| "I'd commit before touching anything else" | Only at the plan's commit steps. |
| "Manual checks get listed as not verified in the final report" | Pause for them. |

## References

- `references/workflow.md`: step detail (drift vs. mismatch, resuming,
  several phases, finish checklist).
- `references/templates.md`: read before the phase-complete pause, a mismatch
  report, or the completion summary.
- `assets/implement-template.md`: read when writing `implement-<slug>.md`.
