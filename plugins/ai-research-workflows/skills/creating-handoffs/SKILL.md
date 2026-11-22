---
name: creating-handoffs
description: >-
  Use when work context must transfer to another session or person: pausing
  work, the context window running out, a collaborator or labmate taking over,
  or picking this up tomorrow in a fresh session. Triggers: create a handoff,
  hand off this work, summarize context for the next session, prepare a
  handoff. Not for an end-of-project repository handover
  (project-management:project-handoff) or one result's provenance
  (ai-research-workflows:ensuring-reproducibility).
metadata:
  capability-network: none
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Creating Handoffs

Produce a handoff document that transfers full working context to the next session with no information loss.

Default mode: Direct (protocol: `ai-research-workflows:using-research-workflows`).

## Process

1. **Gather the true state.** Run `git branch --show-current`, `git rev-parse --short HEAD`, `git status` and `git diff --stat`. Find workflow documents in `docs/rse/specs/` (then legacy `.agents/`), including earlier `handoff-*.md`. Re-run the tests rather than repeating anyone's belief about them. Take tasks and status from the conversation or the user's account, and check them against the repository.
2. **Write it.** Fill `assets/handoff-template.md`: every section that applies, delete the rest, no placeholder text left. Save to `docs/rse/specs/handoff-YYYY-MM-DD-HH-MM-<slug>.md` (current date and time, kebab-case slug), a new file even when an earlier handoff exists.
3. **Present it.** Give the user the file path, phase, status and the prompt that resumes the work.

Read `references/writing-guide.md` when filling the template: per-section guidance, research-state detail, the phase-to-next-skill table, handing off work you did not do, and the summary format.

## Report true state

A handoff that hides broken state sends the next session down a false trail. In a **Known-broken / unverified** callout, name:

- uncommitted and unpushed work;
- failing or unrun tests, by test id, with the status you observed;
- results that are unverified or not yet reproduced.

Leave the working tree as you found it. Don't commit, stash or revert work to make the handoff tidy.

## Quick reference

| Capture | Template section |
| --- | --- |
| Branch, short commit, uncommitted changes | header; Verification State |
| Tasks with status; the workflow phase | Task(s) |
| Workflow documents, linked by filename | Workflow Artifacts |
| The 2-3 files to read first | Critical References |
| Changes as `path:line` references, checked against the file | Recent Changes |
| Seeds, lockfile, data versions, checkpoints, in-flight jobs with the command to check and resume them | Reproducibility & Data State |
| Test status, uncommitted work, unverified results | Verification State / Known-Broken |
| Ordered next steps and the next skill (`implementing-plans` mid-plan, `validating-implementations` once implemented) | Action Items & Next Steps |

## Common mistakes

- **Dumping raw history.** Pasting the conversation or git log buries what matters; distil a focused summary.
- **No starting point.** Name the 2-3 critical files and the exact next skill, not "continue the work".
- **Dropping research state.** Without it the work cannot be resumed or reproduced.
- **Missing learnings.** Record why decisions were made and the dead ends hit.
