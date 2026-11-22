# Presenting, Writing and Reviewing the Research Document

Detail for steps 5 to 9 of the `researching` skill: from findings to a
reviewed `docs/rse/specs/research-<slug>.md` and the hand-off to planning.

## 5. Present findings

Present the synthesized findings in sections, codebase first and then prior
art, with `file:line` anchors for code and citations for external sources.
In Collaborative mode, confirm understanding *before* writing anything out.
In Direct mode, go straight to writing and put the findings in the document.

## 6. Write the document

- Derive a slug from the topic: lowercase, hyphenated (`weekly-aggregate`,
  `retry-libraries`).
- Fill `assets/research-template.md` and write it to
  `docs/rse/specs/research-<slug>.md`. Create `docs/rse/specs/` if it is
  missing.
- Omit the section for any dimension you did not investigate (no empty
  **Codebase Findings** in a prior-art-only document).
- If the internal pass ran, fill the template's **Codebase state** field with
  the commit SHA (`git rev-parse --short HEAD`), next to the **Date**, so the
  `file:line` findings can be re-checked as the code moves. Say so if the
  working tree had uncommitted changes.
- In Direct mode, list the judgment calls you made (scope boundaries, sources
  you skipped, assumptions) in the **Synthesis** section.
- Keep the document self-contained: a planner who reads only this file should
  understand the findings without the conversation.

## 7. Self-review

Before showing the document, read it through with fresh eyes and fix issues
inline:

- [ ] Scope (internal / external / both) is stated.
- [ ] No placeholders: no "TBD", "TODO", empty sections or vague findings.
- [ ] Every codebase finding cites a `file:line`; every prior-art claim cites
      a source, and secondary sources are labelled as such.
- [ ] At least one disconfirming search ran and its result is recorded (if
      the external pass ran).
- [ ] The codebase state (commit SHA and date) is recorded (if the internal
      pass ran).
- [ ] Sections don't contradict each other and the synthesis matches the
      findings.
- [ ] Every scoped sub-question is answered, or its gap is named.
- [ ] Observations are light and labelled; there is no redesign or rewrite
      plan in the document.

## 8. User review

Surface the written document and ask the user to go through it before
moving on:

> Research doc written to `docs/rse/specs/research-<slug>.md`. Please review
> it and tell me if anything is missing or off before we move on to planning.

In Collaborative mode, wait for the response; if they ask for changes,
revise and run the self-review again. In Direct mode, present the document
and proceed to the hand-off, noting that it is ready for their review.

## 9. Hand off

Point to the next skill: usually `ai-research-workflows:planning-implementations`,
which picks up `research-*.md` documents, or
`ai-research-workflows:running-experiments` when the research leaves two or
more approaches that only a measured prototype can decide between.

## Common mistakes

- **Researching both dimensions when one suffices.** A question about what
  the current code does needs no literature search, and a library survey
  needs no codebase trace.
- **Fixing what you find.** A bug found during research is a finding with an
  anchor, not a patch; the fix goes through planning so it gets a test first.
- **Vague codebase findings.** "It's somewhere in auth" is not a finding.
- **Only supporting evidence.** READMEs and project pages describe
  themselves; search for limitations, critiques, benchmark failures and
  deprecations.
- **Turning research into a rewrite plan.** Surface gaps and light
  observations; defer design and critique to planning or validation.
