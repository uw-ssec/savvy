# Writing the handoff

Detail for `SKILL.md` steps 1-3: what to gather, what each template section
needs, and how to present the result. The template is the minimum; include
more when the next session needs it.

## Gathering context

Run these in parallel where possible.

**Git state:** the current branch, the short commit hash, and the uncommitted
changes (`git status` and `git diff --stat`). Note anything committed but not
pushed.

**Workflow documents:** search `docs/rse/specs/`, then legacy `.agents/`, for:

- `research-*.md`: research documents
- `plan-*.md`: plan documents
- `experiment-*.md`: experiment documents
- `implement-*.md`: implementation summaries
- `validation-*.md`: validation reports
- `reproducibility-*.md`: reproducibility records
- `handoff-*.md`: earlier handoffs

**Session context:** what tasks were worked on, the current workflow phase
(Research, Plan, Iterate Plan, Experiment, Implement, Validate, Reproduce,
Harden), and which workflow documents were produced or referenced.

**Test state:** run the test suite and record each failing test by id. If a
test cannot be run here, say so and why; don't infer its status.

**Research state** (research and scientific work; see
`ai-research-workflows:ensuring-reproducibility`):

- random seeds;
- the active environment and lockfile (`pixi.lock`, `uv.lock`);
- dataset paths, versions and checksums;
- partial or intermediate results, checkpoints and outputs, and whether they
  are trustworthy (for example, computed before a bug was fixed);
- long-running jobs still in flight: the job id, the command to check on it
  (for example `squeue -j <id>` or `sacct -j <id>`) and the exact command to
  resume or rerun it.

When a value was not provided and cannot be found, write that it is unknown.
Don't invent it.

## When you did not do the work

The session history may be someone else's, or not available to you (a new
session asked to write a handoff for a person's work). Then:

- take tasks, status and intent from the user's account, and say in the
  handoff that it is their account;
- check every claim you can against the repository: the diff, the tests, the
  workflow documents;
- where the account and the repository disagree, report what the repository
  shows and note the disagreement in the Known-broken / unverified callout;
- if there is nothing to hand off (no account, no changes, no documents), say
  so and ask what the handoff should cover rather than writing an empty one.

## Filling each section

- **Task(s):** every task with its status (complete, in progress, planned) and
  the current phase.
- **Workflow Artifacts:** each document found, by filename, with one line on
  what it holds. Delete artifact types that don't exist. When continuing from
  an earlier handoff, link it as the previous handoff.
- **Critical References:** the 2-3 files the next session must read before
  anything else, each with why. This is the most common cause of a slow
  restart when missing.
- **Recent Changes:** `path/to/file.ext:line` references, not pasted code.
  Open each file and check that the line still points at what you describe.
  Use a code block only for an error being debugged or a pattern that matters.
- **Reproducibility & Data State:** the research state above. Delete the
  section for work with no research state.
- **Verification State / Known-Broken:** the observed test status,
  uncommitted and unpushed work, and unverified results.
- **Learnings:** non-obvious discoveries, root causes, why decisions were made
  and which dead ends were hit, with file paths.
- **Action Items & Next Steps:** an ordered list, specific about what and
  where, ending with the recommended next skill.

Leave no bracketed placeholder text in the saved file.

## Recommended next skill

| Where the work is | Next skill |
| --- | --- |
| Question not yet understood | `ai-research-workflows:researching` |
| Approach not designed, or the plan must change | `ai-research-workflows:planning-implementations` or `ai-research-workflows:iterating-plans` |
| An approach must be tested before committing to it | `ai-research-workflows:running-experiments` |
| Plan approved, mid-execution | `ai-research-workflows:implementing-plans` |
| Implementation done, needs checking | `ai-research-workflows:validating-implementations` |
| Results must be made reproducible | `ai-research-workflows:ensuring-reproducibility` |
| Research code needs tests and robustness | `ai-research-workflows:hardening-research-code` |

In Claude Code and Cursor, the matching slash commands (`/implement`,
`/validate` and so on) also work; in other clients, name the skill.

## Presenting the handoff

After saving, reply with:

```
## Handoff Created

**File:** `docs/rse/specs/handoff-<timestamp>-<slug>.md`
**Current Phase:** [phase]
**Status:** [brief status of work]

### Quick Summary
[2-3 sentences: what was done and what's next]

### For the Next Session
Start by running:
> Read the handoff document at `docs/rse/specs/handoff-<timestamp>-<slug>.md` and resume the work described within.

Or continue with the workflow:
> [recommended-skill] [relevant arguments]
```

The next session finds the handoff through the path in this summary.
