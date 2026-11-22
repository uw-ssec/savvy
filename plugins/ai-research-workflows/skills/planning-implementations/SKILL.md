---
name: planning-implementations
description: >-
  Use when a feature, refactor, or multi-file change needs to be designed before
  coding. Triggers: plan X, design the implementation, how should we build X,
  map out how we'd do it, create an implementation plan, phased plan, success
  criteria, design before coding. Not for changing an existing plan (use
  iterating-plans) or executing an approved one (use implementing-plans).
metadata:
  capability-network: none
  capability-shell: none
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Planning Implementations

Produce a phased implementation plan grounded in the code as it is, with
test-first tasks, measurable success criteria, and every decision made.

## When to use

- A feature, refactor or multi-file change needs a design before anyone codes.
- Not when a plan already exists: use `ai-research-workflows:iterating-plans`.
- Not when the approach is genuinely uncertain: compare prototypes with
  `ai-research-workflows:running-experiments` first.
- Not for a one-line fix or for explaining code.

## Mode

Default: **Collaborative** (protocol: `ai-research-workflows:using-research-workflows`).
Planning is design work, so a specific request to plan still starts
Collaborative. Use Direct only when the user says so ("just write the plan") or
can't be consulted ("I'm offline, leave it for review"); then make the
remaining decisions yourself and record them in the plan.

## Process

1. **Gather context.** Read every mentioned file completely. Check
   `docs/rse/specs/` (then legacy `.agents/`) for `research-*`, `prior-art-*`
   and `experiment-*` docs. If there is no research doc, suggest
   `ai-research-workflows:researching` and proceed as the user prefers. Trace
   existing patterns, integration points and tests. Ask only what the code
   can't answer.
2. **Stop and confirm (Collaborative).** Present what you found, with
   `file:line` references, then design options with pros, cons and a
   recommendation, or a phased breakdown (one-line objective per phase, plus
   what is out of scope). Ask for approval. Don't write the plan file yet.
3. **Write the plan.** Read `references/plan-writing.md` first, then fill in
   `assets/plan-template.md` and save it to `docs/rse/specs/plan-<slug>.md`.
4. **Review.** Summarize the approach, phases and criteria; ask for feedback.
   Revisions go through `ai-research-workflows:iterating-plans`; execution
   through `ai-research-workflows:implementing-plans`.

## Hard rules

- **No open questions.** If something is unresolved, read the code or ask the
  user before saving. This holds when the user asks to leave a decision open:
  explain that the implementer would have to guess, offer the options with a
  recommendation, and ask them to choose. The saved plan has no "Open
  Questions" section.
- **No placeholders.** No "TBD", "add appropriate error handling", "write
  tests for the above" or "similar to Phase N". Show the code or command.
- **Test-first tasks.** Each unit of work: failing test, watch it fail, minimal
  code, watch it pass, commit. For research code the failing test checks a
  known result, analytic case or invariant
  (`ai-research-workflows:hardening-research-code`).
- **Split success criteria** into Automated (runnable commands) and Manual
  (human judgment).
- **Fill in "What We're NOT Doing"**, even for a small plan.

## Quick reference

| Need | Read |
|---|---|
| Required sections, task shape, placeholder list, criteria split, checklist | `references/plan-writing.md` |
| The plan skeleton | `assets/plan-template.md` |
