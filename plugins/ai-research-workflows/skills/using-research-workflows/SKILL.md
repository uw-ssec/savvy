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

This meta-skill routes you to the right skill; the work happens there.

## The rule

If there is even a 1% chance a workflow skill applies, invoke it BEFORE acting:
before editing, and before reading code to "just check" ahead of a change. Drop
it if it doesn't fit. Right-size: the minimal matching skill (a scoped
`researching` pass, a short plan), never **zero skills** for a code change or a
research investigation.

## Instruction priority

1. **The user's explicit instructions** — highest.
2. **These workflow skills** — override default behavior.
3. **The default system prompt** — lowest.

- If the user explicitly skips a named step ("no plan, just write it"), skip
  that step and still run the rest.
- If the user only signals urgency ("just fix it", "don't overthink it"),
  select **Direct** mode and still invoke the matching skill.
- A directive ("add retry logic") states WHAT to do; it skips nothing.

## Choosing a skill (decision tree)

```text
Only asking how existing code works?         → answer from the code, no skill
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

Invoke each as `ai-research-workflows:<name>`.

**Sequence:** understand (`researching`, then `planning-implementations` for
anything non-trivial) → build (`implementing-plans`) → verify
(`validating-implementations`, plus `ensuring-reproducibility` /
`hardening-research-code` when a result will be reported or relied on).

## Interaction modes

Every workflow skill picks **Collaborative** (one question at a time, gate on
approval) or **Direct** (act, narrate briefly, stop only when blocked).
Destructive or outward-facing actions always need confirmation.

## Red flags — you're about to skip a skill

| Thought | Reality |
|---|---|
| "5 minutes — don't overthink it" | Direct mode, scoped skill. Don't skip it. |
| "I'll just tweak the code real quick" | Understand first → `researching`. |

## References

- `references/workflow-patterns.md` — read when choosing how much of the chain
  to run, or for the full red-flags table and common mistakes.
- `references/conventions.md` — read before writing or finding a workflow
  document (`docs/rse/specs/`), or to defer environments, tests or packaging.
- `references/interaction-modes.md` — read when selecting a mode.
