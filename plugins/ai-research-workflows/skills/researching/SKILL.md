---
name: researching
description: >-
  Use when a task needs desk research before planning or building: documenting
  how existing code works before changing it, or finding out whether a method
  or library already exists. Triggers: research how X works before changing
  it, trace the call path, has this been done before, is there already a lib
  for X or do I write it myself, prior art, survey approaches, literature
  review. Not for timing prototypes against each other (running-experiments)
  or writing the plan (planning-implementations).
metadata:
  capability-network: read
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Researching

Desk research that feeds planning: the current codebase (internal), published
work and tools (external), or both, written up as one research document.

## When to use

- Documenting, before a change, how the code involved works and what depends on it.
- Learning whether a method or library exists and how options compare on published evidence.
- **Not** for a quick "how does X work?" with no change planned: answer from the code.
- **Not** for building and timing prototypes (`ai-research-workflows:running-experiments`) or writing the plan (`ai-research-workflows:planning-implementations`).

## Interaction mode

Default **Collaborative**: state the scope and research plan (or ask one
focused scoping question) and get a quick OK before investigating; present
findings before writing. Use **Direct** when the user gives a specific
directive with enough context or won't be available: state scope and plan,
proceed, write the document, and note judgment calls in it. Mode rules:
`ai-research-workflows:using-research-workflows`.

## Quick reference

| Step | Gate | Artifact |
|---|---|---|
| 1. Context: the request, `docs/rse/specs/research-*.md` (legacy: `.agents/`, `prior-art-*.md`), recent commits | | |
| 2. Scope: internal, external or both; relevance; depth | State it | |
| 3. Plan: codebase sub-questions to trace, and/or sources and comparison dimensions | Quick OK (Collaborative) | |
| 4. Investigate: `references/codebase-research.md` (internal), `references/prior-art-research.md` (external) | | |
| 5. Present findings | Confirm (Collaborative) | |
| 6. Write from `assets/research-template.md` | | `docs/rse/specs/research-<slug>.md` |
| 7. Self-review the written document | Fix inline | |
| 8. Ask the user to review it | Wait (Collaborative) | |
| 9. Hand off to `planning-implementations`, or `running-experiments` if an approach is uncertain | | |

At step 6, read `references/writing-and-review.md` (slug, codebase state,
self-review checklist, review request).

## Hard rules

- **Scope first.** Don't search prior art for a question about current code, or the reverse.
- **Every codebase finding cites `file:line`.** "Somewhere in the session module" is not a finding.
- **Record the codebase state**, commit SHA (`git rev-parse --short HEAD`) and date, when the internal pass ran.
- **Every prior-art claim cites a source**, primary where possible, secondary labelled. Run at least one disconfirming search for limitations, critiques and failures.
- **Describe, don't change code.** A bug you find goes in the document with its anchor; the fix goes to planning.
- **Self-review before showing the document:** no placeholders or TBDs, anchors and citations present, no contradictions, every sub-question answered or its gap named.
