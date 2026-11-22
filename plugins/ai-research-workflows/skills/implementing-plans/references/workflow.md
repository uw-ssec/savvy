# Implementing Plans — Workflow Detail

The step-by-step detail behind the workflow in `SKILL.md`. The templates named
here are in `templates.md` next to this file.

## 1. Load the plan

If no plan path is given, list the candidates:

```bash
ls -lt docs/rse/specs/plan-*.md .agents/plan-*.md 2>/dev/null
```

In Collaborative mode, ask which one to implement; in Direct mode, take the
most recent one that matches the request and say which you picked.

Once the plan is identified:

- Read the **entire plan**. Partial reads miss phases, dependencies and
  success criteria.
- Note existing checkmarks (`- [x]`): that work is already done.
- Read **every file the plan mentions**, completely. Partial reads cause bugs.
- Understand the full scope, architecture and dependency order before starting.
- Create one task per phase to track progress.

## 2. Review the plan before building

The plan is not infallible. Before writing any code:

- **Sanity-check the approach.** Note questions, gaps or concerns about the
  design, the phase order or the success criteria. If anything looks wrong or
  unclear, raise it with the user before starting. Don't silently "fix" the plan
  by improvising.
- **Confirm the plan's assumptions still hold.** Research code often depends on
  data being present, specific dependency versions, random seeds or a
  particular environment. Check that they are in place. If a prerequisite is
  missing, say so now rather than failing mid-phase.
- **Confirm the working branch** with `git branch --show-current`. On `main` or
  `master`, don't write code without the user's explicit consent, in any
  interaction mode. Creating a local feature branch is fine: name it, say you
  created it, and work there.

If the plan is sound and the branch is set, say so in one line and proceed. If
not, stop and resolve the concerns first.

## 3. Implement one phase

- Implement one phase fully before moving to the next. Don't jump ahead.
- Follow existing code patterns. Don't introduce inconsistencies.
- Edit the plan file as you go: change a task's `- [ ]` to `- [x]` when it is
  done, so the user can follow progress in the plan.
- Commit where the plan's tasks say to (for example a "Commit:" task), on the
  feature branch, or on `main`/`master` only if the user explicitly consented
  to working there. If the plan has no commit steps, don't commit; list the
  uncommitted changes in the summary.
- When a phase produces a result, figure, metric or trained artifact, capture
  its provenance (environment, data version, seeds, exact commands) with
  `ai-research-workflows:ensuring-reproducibility` so it can be reproduced.

### Drift or mismatch?

The codebase rarely matches a plan exactly. Decide which case you are in:

- **Drift** (adapt, then record it): the plan's intent can be carried out
  exactly as written, and only an incidental detail differs, such as a shifted
  line number, a renamed local variable, or an import that moved within the
  same file. Make the change and record it under "Deviations from Plan" in the
  implementation summary.
- **Mismatch** (stop and ask): a file, function, class or signature the plan
  says already exists is not where the plan says, or is different (files and
  functions the plan tells you to create are not mismatches); a prerequisite (data,
  dependency, environment) is missing; the plan's step would fail or change
  behavior the plan didn't intend; or doing it would take you outside the
  plan's scope. Stop and present the "Issue in Phase" report from
  `templates.md`, then wait. Let the user decide whether to adjust the plan
  (`ai-research-workflows:iterating-plans`), proceed with the original intent,
  or research further.

If you are unsure which case applies, treat it as a mismatch. A user's hint
("I think it moved, go ahead anyway") is not a decision about where the change
goes: check, and if it is a mismatch, still report it and wait.

## 4. Verify the phase

Run every command in the plan's automated verification for this phase (the
phase's own "Verification" list and the matching items under "Success
Criteria → Automated Verification"). For each, record the command and its
result:

Also run the existing test suite: the phase must add the tests the plan calls
for, test any new behavior even where the plan names no test, handle the
failure paths it introduces (no silently swallowed errors), and introduce no
regressions.

- Passes: note the output.
- Fails: investigate and fix before going on. Don't move to the next phase on a
  failing check.

## 5. Pause for manual verification

Automated checks passing is not enough. After they pass, present the "Phase
Complete / Ready for Manual Verification" message from `templates.md`, listing
the plan's manual checks, and wait for the user's confirmation before the next
phase.

Don't tick manual verification items in the plan until the user confirms they
are done. "Make it look finished" is not a confirmation.

### Several phases in one go

If the user asks for several phases consecutively ("implement phases 1-3",
"do both phases, I'll check at the end"):

- Run the automated verification after **each** phase, and fix failures
  immediately.
- Skip the manual-verification pause until the **last** of those phases.
- At the end, pause once with every phase's manual checks listed, still
  unticked.

## Resuming work

If the plan already has checkmarks (`- [x]`):

- Trust that checked work is done. Don't re-implement completed phases.
- Start at the first unchecked item (`- [ ]`).
- Re-verify earlier work only if tests fail, files are missing or something is
  inconsistent. A checked phase whose files don't exist is a mismatch: report
  it.
- Still check the prerequisites the remaining phases depend on (for example,
  that a data directory exists) before writing code that uses them.

## If you get stuck

1. Make sure you have read all relevant files completely.
2. Consider whether the codebase has changed since the plan was written.
3. Present the mismatch with the "Issue in Phase" template in `templates.md`.
4. Don't guess or make assumptions.
5. Use sub-tasks sparingly: for targeted debugging or exploring unfamiliar
   code, never for the implementation itself.

## 6. Finish and summarize

Before declaring the implementation done, confirm it is:

- [ ] Every phase is implemented and its tasks are ticked in the plan.
- [ ] Every phase's automated verification passes now (re-run them).
- [ ] No plan task was silently skipped; any skipped or changed task is listed
      as a deviation.
- [ ] Tests the plan calls for, and tests for any other new behavior, are
      written and passing, with no regressions.
- [ ] The changes are on a feature branch, not left on `main`/`master`
      (unless the user explicitly consented to working there).
- [ ] Every phase task in your task list is done, and no open issue or
      blocker remains. If one does, the implementation is not done: report
      it and stop.
- [ ] Manual verification items are listed for the user and left unticked
      unless the user confirmed them.

Then write the summary:

1. **Name it** from the plan's slug: `plan-jwt-auth.md` → `implement-jwt-auth.md`.
2. **Read the template** at `assets/implement-template.md`.
3. **Fill every section:** plan reference, phases completed, files modified,
   tests run, verification results (automated, and manual as confirmed or
   pending), deviations, issues encountered, key changes, remaining work and
   next steps.
4. **Save it** to `docs/rse/specs/implement-<slug>.md` and confirm the path.
5. **Present the completion summary** from `templates.md`, and route to
   `ai-research-workflows:validating-implementations` as the next step.

## Related skills

Follows `ai-research-workflows:planning-implementations` (and
`ai-research-workflows:iterating-plans` when a plan changes). Verify the result
with `ai-research-workflows:validating-implementations`. For research code,
capture provenance with `ai-research-workflows:ensuring-reproducibility` and
robustness with `ai-research-workflows:hardening-research-code`.
