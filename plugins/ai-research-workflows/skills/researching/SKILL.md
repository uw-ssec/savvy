---
name: researching
description: >-
  Use when desk research must come before planning: documenting how existing
  code works, or tracing where a wrong result comes from, before a change or
  fix is planned; or checking whether a method or library exists.
  Triggers: research how X works before changing it, trace the code, has this
  been done before, what tools or libraries exist for X, prior art, survey
  approaches, literature review. Not for timing prototypes
  (running-experiments) or writing the plan (planning-implementations).
metadata:
  capability-network: read
  capability-shell: runs-commands
  capability-file: write
  capability-environment: none
  capability-mcp: none
---

# Researching

Desk research for planning: the current codebase (internal pass), external
prior art (papers, tools), or both, in one research document.

## When to use

- Before a change: how the code works and what depends on it.
- Whether a method or library exists; how options compare on published evidence.
- **Not** for a quick "how does X work?" with no change planned: answer directly.
- **Not** for building and timing prototypes (`ai-research-workflows:running-experiments`) or writing the plan (`ai-research-workflows:planning-implementations`).

## Interaction mode

Default **Collaborative**: state the scope and research plan (or ask one
focused scoping question) and get a quick OK before investigating; present
findings before writing. Use **Direct** when the user gives a specific
directive with enough context or won't be available: state scope and plan,
proceed, write the document, noting judgment calls. See
`ai-research-workflows:using-research-workflows`.

## Quick reference

Track steps as tasks.

| Step | Gate | Artifact |
|---|---|---|
| 1. Context: the request, `docs/rse/specs/` research and plan docs (legacy: `.agents/`, `prior-art-*.md`), recent commits | | |
| 2. Scope: internal, external or both; relevance; depth | State it | |
| 3. Plan: codebase sub-questions to trace, and/or sources and comparison dimensions | Quick OK (Collaborative) | |
| 4. Investigate: `references/codebase-research.md` (internal), `references/prior-art-research.md` (external) | | |
| 5. Present findings | Confirm (Collaborative) | |
| 6. Write from `assets/research-template.md` | | `docs/rse/specs/research-<slug>.md` |
| 7. Self-review the document | Fix inline | |
| 8. Ask the user to review it | Wait (Collaborative) | |
| 9. Hand off: `planning-implementations`, or `running-experiments` if an approach is uncertain | | |

Before step 5, read `references/writing-and-review.md` (presenting, slug,
codebase state, checklists).

## Hard rules

- **Scope first.** Skip the prior-art pass for a current-code question, and vice versa.
- **Every codebase finding cites `file:line`.** "Somewhere in the session module" is not a finding.
- **Record the codebase state** (commit SHA via `git rev-parse --short HEAD`, and date) when the internal pass ran.
- **Every prior-art claim cites a primary source**; label any secondary source. Run at least one disconfirming search for limitations, critiques and failures.
- **Describe; don't change code or draft the fix.** A bug you find, even a one-liner, goes in the document with its anchor; the fix goes to `planning-implementations`.
- **Self-review before showing the document:** no placeholders (TBD), anchors and citations present, no contradictions, every sub-question answered or its gap named.
