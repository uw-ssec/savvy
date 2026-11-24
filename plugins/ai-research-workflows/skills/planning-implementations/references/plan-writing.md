# Writing the Plan

Read this before you write `docs/rse/specs/plan-<slug>.md`. It covers what goes
in each section, how to shape the tasks, the placeholder list, and the checklist
to run before saving. `assets/plan-template.md` is the file you fill in.

## Required sections

Fill in every section of the template. These nine must always have real content:

1. **Overview**: what, why, and the high-level how.
2. **Current State Analysis**: the existing code, with `file:line` references.
3. **Desired End State**: observable outcomes that mean success.
4. **What We're NOT Doing**: explicit scope boundaries. Fill it in even when the
   answer seems obvious; it is what stops scope creep.
5. **Implementation Approach**: the technical strategy and key decisions, with
   the alternatives considered.
6. **Implementation Phases**: phased tasks with file paths and verification.
7. **Success Criteria**: split into Automated and Manual (see below).
8. **Testing Strategy**: integration and manual coverage beyond the per-phase
   unit tests, plus test data.
9. **References**: research docs, experiment reports, files analyzed and
   external docs, as relative markdown links.

The other template sections (Migration Strategy, Risk Assessment, Edge Cases,
Performance, Documentation, Timeline) are kept when they apply and deleted when
they don't. Never leave a section holding template text.

## Phase shape

Each phase has a clear objective, its tasks, its dependencies on earlier phases,
and a verification step: the exact command that shows the phase is done, with
the expected output.

Reference an exact `path/to/file.ext:line` for every task that touches existing
code. For a file the plan creates, give its path and mark it `(new)`.

## Bite-sized, test-first tasks

Tasks are executable steps an engineer can follow without guessing. Write the
actual content, not a description of it.

- Sequence each unit of work as: write the failing test, run it and watch it
  fail, implement the minimal code, run the test and watch it pass, commit.
- Show the actual code or the exact command for every step that changes code
  or runs something. Never a paraphrase.
- Keep unit tests inside the phase that needs them. Don't collect them into a
  trailing Testing Strategy section or a final "add tests" phase.

For numerical or research code, the failing test is an assertion against a
known result, an analytic case or an invariant (for a spectrum, Parseval's
theorem), compared with a justified tolerance rather than `==`. See
`ai-research-workflows:hardening-research-code`. A plan that produces a
reported result also fills the template's Reproducibility & Correctness block
(see `ai-research-workflows:ensuring-reproducibility`).

## Placeholders

A step that says *what* to do without showing *how* is a plan failure. Resolve
each of these before saving:

- "TBD", "TODO", "implement later", "fill in details".
- "Add appropriate error handling", "add validation", "handle edge cases":
  name each specific case and show how it is handled and tested.
- "Write tests for the above" without the test code.
- "Similar to Phase N": repeat the code, because phases may be executed out of
  order.
- Any type, function or file that no task defines.
- Leftover template text such as `[Feature/Change Name]` or `[YYYY-MM-DD]`.

## Success criteria split

**Automated Verification**: commands an agent can run without a person, each
with the expected result (`pytest tests/ -v`, a script that prints a value
within a stated tolerance, a linter, a file-existence check).

**Manual Verification**: steps that need human judgment (UI behavior, agreement
with an external reference such as published tables, performance under real
conditions).

"Works well" and "tests pass" are not criteria. Turn each into a runnable
command with an expected result, or into an observable outcome a person can
check.

## Resolved decisions

Every decision the plan depends on is made before the plan is saved. Record
each one under the template's **Resolved Decisions** heading: the decision, who
made it (the user, the team, or you in Direct mode), and why. If the list would
hold a question rather than an answer, the plan is not ready: go back to the
code, or ask the user.

## Common mistakes

- **Confirming the approach too late**: writing every phase in detail before the
  user approved the strategy. In Collaborative mode, get sign-off first.
- **Tests bolted on at the end**: a test phase after the implementation phases
  produces tests-last code.
- **Vague or unsplit success criteria**: hides what needs a person and what a
  command can check.
- **An "Open Questions" list in the saved plan**: ships the ambiguity to the
  implementer, who will guess.
- **Skipping "What We're NOT Doing"** because the plan is small.

## Checklist before saving

- [ ] Every file the plan relies on was read completely.
- [ ] Research and experiment docs are incorporated and linked in References.
- [ ] In Collaborative mode, the user approved the approach and the phasing.
- [ ] The plan follows `assets/plan-template.md` and is saved to
      `docs/rse/specs/plan-<slug>.md`.
- [ ] Every task has a `file:line` reference, or a path marked `(new)`.
- [ ] Every phase is test-first, with real test code and exact commands.
- [ ] No placeholders from the list above.
- [ ] Success criteria are split into Automated and Manual, and each is concrete.
- [ ] "What We're NOT Doing" is filled in.
- [ ] Resolved Decisions holds answers only; no open questions remain.
