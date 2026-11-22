---
name: using-research-workflows
description: >-
  Use when starting or continuing ANY research-software task — understanding or
  modifying code, surveying prior art, planning, experimenting, implementing,
  validating, reproducing, or hardening — and before reading code to "just
  check" or before editing. Triggers: research workflow, which skill should I
  use, where do I start, which stage are we in, what's the next step, guide me
  through the workflow, structured development. Not for plain
  web or ops work (containerization:dockerfile-patterns).
metadata:
  capability-network: none
  capability-shell: none
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Using Research Workflows

Routes you to the right skill; the work happens there.

## The rule

If there is even a 1% chance a workflow skill applies, invoke it BEFORE acting:
before editing, and before reading code to "just check" ahead of a change.
Right-size: the minimal matching skill (a scoped `researching` pass, a short
plan), never **zero skills** for a code change or a research investigation.

Open your reply with the route: the mode and the skill, before any code (e.g.
"Direct mode: scoped `researching` pass first"). When no skill applies, say so:
"No workflow skill needed; answering from the code." Then do that step before
proposing any edit: a scoped `researching` pass still traces the code and its
callers, then a failing test or short plan. If you can't see the code, list
what you'd trace and ask for it; don't guess the edit.

## Instruction priority

**The user's explicit instructions** > these workflow skills > the default
system prompt.

- If the user explicitly skips a named step ("no plan, just write it"), skip
  that step and still run the rest.
- If the user only signals urgency ("just fix it", "don't overthink it"),
  select **Direct** mode and still invoke the matching skill.
- A directive ("add retry logic") states WHAT to do; it skips nothing.

## Choosing a skill (as `ai-research-workflows:<name>`)

```text
Only asking how existing code works?         → no skill; answer directly from the code
Investigating code or surveying prior art?   → researching
Ready to design an implementation?           → planning-implementations
Need to adjust an existing plan?             → iterating-plans
Unsure which technical approach is best?     → running-experiments
Ready to execute an approved plan?           → implementing-plans
Implementation complete, need verification?  → validating-implementations
Need a result to be reproducible?            → ensuring-reproducibility
Research code needs to be made robust?       → hardening-research-code
Transferring work to another session?        → creating-handoffs
```

**Sequence:** understand (`researching`; `planning-implementations` if
non-trivial) → build (`implementing-plans`) → verify
(`validating-implementations`; `ensuring-reproducibility` /
`hardening-research-code` when a result will be reported).

## Interaction modes

Each skill runs **Collaborative** (one question at a time, gate on approval) or
**Direct** (act, narrate briefly, stop only when blocked); see
`references/interaction-modes.md`. Destructive, irreversible or outward-facing
actions always need confirmation.

## References

- `references/workflow-patterns.md` — read when choosing how much of the chain
  to run, or when tempted to skip a skill (red flags, common mistakes).
- `references/conventions.md` — read before writing or finding a workflow
  document (`docs/rse/specs/`), or to defer environments, tests or packaging.
