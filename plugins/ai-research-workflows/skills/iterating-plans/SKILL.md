---
name: iterating-plans
description: >-
  Use when an existing implementation plan (`docs/rse/specs/plan-*.md`) needs
  changes before or during execution. Triggers: update the plan, change the
  plan, revise the plan, add a phase, split a phase, reorder or drop a phase,
  revise scope, cut scope, fix success criteria, incorporate experiment
  results, review feedback on a plan. Not for writing a first plan
  (`ai-research-workflows:planning-implementations`) or executing an approved
  one unchanged (`ai-research-workflows:implementing-plans`).
metadata:
  capability-network: none
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Iterating Plans

Revise an existing plan in place with surgical, consistent edits.

Default mode: Collaborative (protocol: `ai-research-workflows:using-research-workflows`).

## Process

1. **Read.** If the plan or the change is missing, ask (recent plans:
   `ls -lt docs/rse/specs/plan-*.md .agents/plan-*.md 2>/dev/null | head -5`).
   Read the whole plan and any `experiment-*.md` the change draws on.
2. **Research only if the change adds technical requirements or alters the
   approach:** find real `path/file.ext:12-30` anchors; never guess a path.
3. **Propose, keyed to the mode.**
   - *Collaborative* (default, including a bare "go" or a specific request:
     this skill overrides the protocol's step 2, which would pick Direct for
     a specific directive, because a plan edit changes what later agents
     execute): reply with
     **Current state** (phases), **Proposed changes**, **Sections affected**,
     then "Does this match?" Don't touch the file until the user says yes.
   - *Direct* (the user says not to check back: "no need to check back",
     "don't ask", "just do it", "go ahead"): list the intended edits, then apply them. Example:
     "Applying: insert Phase 2, renumber old Phases 2–3 to 3–4."

   Push back on changes that conflict with existing phases.
4. **Edit surgically in place** per the Quick Reference, matching the existing
   phase format. Never regenerate the plan or reformat untouched sections.
5. **Consistency scan (required)** after every edit:
   1. Renumber later phases: numbers are monotonic and contiguous.
   2. Update every cross-reference (dependencies, "(Phase N)" in success
      criteria and testing strategy, file anchors) to the new numbering.
   3. Nothing references a removed task, phase, function or file.
   4. Each phase keeps its Automated / Manual Verification split.
   5. No open question or placeholder entered the plan: research it or ask.
6. **Research-criteria re-check (required when the approach changes or a
   results-producing phase is added):** the Reproducibility & Correctness
   criteria (seeds, provenance, tolerances) still hold and cover the new work.
7. **Report** the changes by section and their effect on criteria.

Read `references/iteration-patterns.md` for the step 3 and 7 messages and a
worked pattern per change.

## Quick Reference

| Change | Touch | Leave alone |
|---|---|---|
| Add a phase | New phase (each task names its file, cites `path/file.ext:12-30` for existing code it changes or calls, marks new files as new; test first; Automated/Manual criteria); later numbers and references | Other phases |
| Add a task | The task in its phase: names its file, cites `path/file.ext:12-30` for existing code it changes or calls, marks new files as new; its success criteria | Other tasks and phases |
| Cut scope | Its tasks, success criteria and tests; add it to "What We're NOT Doing" with the reason | Unrelated phases |
| Update criteria | The items, in the right Automated or Manual list | Tasks |
| New approach or experiment results | Implementation Approach; affected tasks; References (link the report); research criteria | Unaffected phases; Current State Analysis unless the results disprove it |
| Split or reorder | The phases, each independently testable; later numbers and references | Tasks that don't move |

## Common Mistakes

- Deleting cut tasks without adding them to "What We're NOT Doing" or removing their success criteria.
- Inserting a phase without renumbering later phases and their cross-references.
- Editing before confirming in Collaborative mode, or saving an "Open question" in the plan.
