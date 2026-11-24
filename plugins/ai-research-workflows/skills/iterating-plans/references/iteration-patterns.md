# Iterating Plans — Messages and Common Iteration Patterns

- [Research (step 2)](#research-step-2)
- [Proposal message (step 3)](#proposal-message-step-3)
- [Plan Updated message (step 7)](#plan-updated-message-step-7)
- [Edits that are and aren't surgical](#edits-that-are-and-arent-surgical)
- [Common iteration patterns](#common-iteration-patterns)

## Research (step 2)

Research is needed when the change introduces new technical requirements or
alters the approach; structural changes (reordering, splitting), clarifications
and minor scope adjustments don't need it. When it is needed, investigate in
parallel: how the new requirement is handled today, examples of the pattern the
new phase should follow, dependencies of a new component, and the tests covering
the area. Wait for all research to finish, then synthesize which files to add to
tasks, which patterns to reference, which success criteria to add and which
risks to note. Verify technical feasibility before adding a task, and question
vague feedback ("when you say 'more robust', do you mean...?").

## Proposal message (step 3)

This skill confirms by default even for a specific request, because an edited
plan changes what a later agent will execute; only an explicit "don't check
back" selects Direct. In Collaborative mode, present this before any edit and wait for a yes. If the
user says no, clarify and adjust; only proceed on yes. In Direct mode, give the
"Proposed changes" and "Sections affected" lists as a statement of what you are
about to do, then edit.

```
I've read the plan and understand you want to [summary of requested changes].

Current state:
- Phases: [list]
- Scope: [summary]

Proposed changes:
- [Change 1]
- [Change 2]

Sections affected:
- [Section 1]
- [Section 2]

[If research was done] Key findings:
- [Finding]

Does this match what you're looking for?
```

## Plan Updated message (step 7)

```
# Plan Updated

Changes to `docs/rse/specs/plan-[slug].md`:

## Changes Made
- [Change 1 — specific section]
- [Change 2 — specific section]

## Impact
- [How changes affect implementation]
- [New/removed success criteria]

Would you like any further adjustments?
```

If the user wants more changes, re-read the plan first and apply the same
process. When the plan is settled, execute it with the
`ai-research-workflows:implementing-plans` skill.

## Edits that are and aren't surgical

**Good edits:** add a new phase section between existing phases; update specific
success criteria items; modify task descriptions within a phase; add file
references to existing tasks.

**Bad edits:** replace the entire plan; rewrite sections that don't need
changes; change formatting or structure unnecessarily.

When scope changes, update the success criteria (add or remove items) and keep
the Automated vs. Manual split:

```markdown
### Automated Verification
[Commands and checks that run without human intervention]

### Manual Verification
[Steps requiring human testing and judgment]
```

Keep the plan's sections in step: scope changes update "What We're NOT Doing";
approach changes update "Implementation Approach"; new tasks reference actual
codebase examples.

Edit the plan at its existing path (`docs/rse/specs/plan-*.md`, or a legacy
`.agents/plan-*.md`); results of `docs/rse/specs/experiment-*.md` (or legacy
`.agents/experiment-*.md`) feed the approach. For the research-criteria
re-check (step 6), the `ai-research-workflows:ensuring-reproducibility` and
`ai-research-workflows:hardening-research-code` skills define what the
reproducibility and numerical-correctness criteria should cover.

## Common iteration patterns

The "Confirm" step below is the Collaborative-mode check-in; in Direct mode,
state the same sentence as what you are doing and continue.

### Adding a phase

1. Read surrounding phases; research codebase patterns if needed.
2. Confirm: "I'll add a new Phase N for [topic], shifting current Phase N to
   Phase N+1. Tasks: [list]. OK?"
3. Edit the plan to insert the phase; update phase numbering and cross-references.

### Updating success criteria

1. Read current criteria; determine Automated vs. Manual classification.
2. Confirm the addition (e.g., `curl` command → Automated, format check → Manual).
3. Edit the plan to add to the appropriate section.

### Adjusting scope

1. Find all references to the feature being removed.
2. Confirm: "I'll remove [feature] tasks from [phase] and add it to 'What
   We're NOT Doing'. Does that cover it?"
3. Edit the plan to remove tasks, update scope section, and remove related criteria.

### Incorporating experiment results

1. Read the experiment report (`experiment-*.md`) to understand the chosen approach.
2. Identify where the old approach is referenced.
3. Confirm: "I'll update Implementation Approach and Phase N tasks to use
   [approach B]. This affects [files]. Correct?"
4. Edit the plan to update approach section and affected tasks; add experiment report
   to References.

### Splitting a complex phase

1. Read the phase; identify a logical split point.
2. Confirm: "I'll split Phase N into Phase N (tasks 1-X: [objective A]) and
   Phase N+1 (tasks X+1-Y: [objective B]). Each phase will be independently
   testable. Sound good?"
3. Edit the plan to split; update subsequent phase numbering.

## Common Mistakes

- Deleting cut tasks without adding them to "What We're NOT Doing" or removing their success criteria.
- Inserting a phase without renumbering later phases and their cross-references.
- Editing before confirming in Collaborative mode, or saving an "Open question" in the plan.
