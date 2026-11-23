---
name: planning-implementations
description: >-
  Use when a feature, refactor, or multi-file change needs to be designed before
  coding. Triggers: plan X, design the implementation, how should we build X,
  create an implementation plan, phased plan, success
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

Produce a phased plan grounded in the actual code, with test-first tasks,
measurable success criteria, and every decision made.

## When to use

- A feature, refactor or multi-file change needs designing before code.
- Not when a plan already exists: use `ai-research-workflows:iterating-plans`.
- Not when the approach is genuinely uncertain: run
  `ai-research-workflows:running-experiments` first.
- Not for one-line fixes or explaining code.

## Mode

Default: **Collaborative** (protocol: `ai-research-workflows:using-research-workflows`).
A plan is design-shaped work, which the protocol gives to Collaborative, so a
specific request to plan still gets the gates below. Use Direct only when the
user says so ("just write the plan") or can't be consulted ("I'm offline");
then skip the gates in steps 2, 3 and 5, decide yourself and record each
choice under Resolved Decisions.

## Process

1. **Gather context.** No topic given? Ask what to plan. Read every mentioned
   file completely. Check `docs/rse/specs/` (then legacy `.agents/`) for
   `research-*`, `prior-art-*` and `experiment-*` docs; with no research doc,
   suggest `ai-research-workflows:researching` and proceed as the user prefers.
   Investigate patterns, integration points, dependencies and tests, in
   parallel where possible; finish all of it before synthesizing. Ask only
   what the code can't answer.
2. **Approach gate.** Present findings with `file:line` references, design
   options with pros, cons and a recommendation, and what is out of scope. Ask
   for approval. Don't write the plan file yet.
3. **Structure gate.** Propose the phases, one-line objective each; get
   feedback.
4. **Write the plan.** Read `references/plan-writing.md` first, then fill in
   `assets/plan-template.md` and save it to `docs/rse/specs/plan-<slug>.md`.
5. **Review.** Give the approach, phase count and criteria counts; ask about
   phasing, criteria, approach and edge cases. Revise with
   `ai-research-workflows:iterating-plans`; execute with
   `ai-research-workflows:implementing-plans`.

## Hard rules

- **No open questions.** Resolve every uncertainty (read the code, or ask)
  before saving, even when the user asks to leave one open: explain that the
  implementer would have to guess, offer options with a recommendation, and
  ask them to choose (in Direct mode, take the recommendation and record it).
  No "Open Questions" section.
- **No placeholders.** No "TBD", "add appropriate error handling", "write
  tests for the above" or "similar to Phase N". Show the test code and commands.
- **Test-first tasks.** Each unit of work: failing test, watch it fail, minimal
  code, watch it pass, commit. For research code the failing test checks a
  known result, analytic case or invariant
  (`ai-research-workflows:hardening-research-code`).
- **Anchor every phase**, including one that only runs or regenerates: cite
  `file:line` for the files it changes or runs, code or docs; mark files it
  creates `(new)`.
- **Split success criteria** into Automated (commands) and Manual (judgment).
- **Fill in "What We're NOT Doing"**, even when small: it stops scope creep.

## Quick reference

| Need | Read |
|---|---|
| Sections, task shape, placeholders, criteria split, checklist | `references/plan-writing.md` |
| The plan skeleton | `assets/plan-template.md` |
