# Versioning and Deprecation Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give uw-ssec/savvy a changelog, a CalVer versioning policy, and a deprecation policy, so users can see what changed between releases and contributors have a written rule for what counts as a breaking change.

**Architecture:** Four prose deliverables, no executable code. `docs/versioning.md` defines how releases and per-plugin manifest versions are numbered; `docs/deprecation.md` defines what protection users get when a name or a skill's intent changes, which under CalVer is the only mechanism that signals breakage; `CHANGELOG.md` gives both a per-release, per-plugin record; `CONTRIBUTING.md` routes contributors to all three. Tasks are ordered so each deliverable only links to documents that already exist.

**Tech Stack:** Markdown. Repo gates: `pixi run plugins-check`, `pixi run plugins-sync`.

**Spec:** [uw-ssec/savvy#130](https://github.com/uw-ssec/savvy/issues/130), as amended by the CalVer comments on that issue. **The issue body is stale** — it specifies per-plugin semver, which was superseded. Every decision that supersedes it is recorded in Global Constraints below, so this plan is self-contained; read Global Constraints, not the issue body, for the rules.

## Global Constraints

- **Scheme:** Ubuntu-style CalVer, repo-wide. `YY.M.MICRO`.
- **No zero-padding anywhere.** `v26.4.0`, never `v26.04.0`. `26.04` is not valid semver and the manifests must stay semver-shaped.
- **Tag and manifest carry the same string.** Tag `v26.11.0` ⇒ manifest `"version": "26.11.0"`. The only difference is the leading `v`.
- **Release examples to use verbatim:** `v26.11.0` (a release), `v26.11.1` (a fix between releases), `v26.4.0` (a single-digit month).
- **Per-plugin rule:** a plugin's manifest version is the release in which that plugin last changed. Unchanged plugins keep their older version.
- **"Changed" is defined mechanically:** `git diff --name-only <prev-tag>..HEAD -- plugins/<name>` (or `community-plugins/<name>`) returns at least one path.
- **Deprecation clock:** removal no earlier than **both** the next release **and** 90 days after the announcement. Whichever is later governs.
- **Preferred deprecation route:** ship the changed behavior as a **new skill** under a new name and deprecate the old one. Deprecate-in-place is the fallback.
- **Manifest editing rule to restate in the policy:** edit `plugin.json` only; `pixi run plugins-sync` regenerates `.claude-plugin/plugin.json`, the catalog entries, `.agents/plugins/marketplace.json`, and `.cursor-plugin/marketplace.json`; `pixi run plugins-check` fails CI on drift.
- **No cadence is stated.** The policy must work without one — that is why the clock has a 90-day floor.
- **Out of scope, do not do:** bumping any `plugin.json` version, running `plugins-sync`, writing any CI check for the bump rule. Those are [#132](https://github.com/uw-ssec/savvy/issues/132) and [#135](https://github.com/uw-ssec/savvy/issues/135).
- **Commit style:** conventional commits, `docs:` prefix, matching existing history.
- **Pre-existing inconsistency, do not fix here:** manifests and `CONTRIBUTING.md` still say `uw-ssec/rse-plugins` while the repo is now `uw-ssec/savvy`. New documents should use `uw-ssec/savvy`; leave the existing stale references alone and mention them in the PR body.

## Review Focus

Five cases the spec implies but never states. Each has a content requirement in the task that owns it.

1. **A plugin added after the first release** — the spec never says what version a brand-new plugin gets. Without a rule an author will invent `0.1.0` and break the scheme. (Task 1)
2. **A change that touches no plugin directory** — a README, CI, or `docs/` edit. A reader will ask whether anything bumps; the answer must be "no plugin version changes." (Task 1)
3. **A micro release that fixes one plugin** — `26.11.1` must leave the other eleven at `26.11.0`. "Release" in the per-plugin rule has to visibly include micros. (Task 1)
4. **Removing a whole plugin** — the deprecation policy covers plugin names, but removal also drops a catalog entry, and the catalog entry must survive until the clock expires. (Task 2)
5. **A deprecation announced with no next release in sight** — if the repo goes quiet, the 90-day floor alone must not authorize removal; the release clause still has to be satisfied. (Task 2)

---

### Task 1: Versioning policy

**Files:**
- Create: `docs/versioning.md`

**Interfaces:**
- Produces: the anchor `docs/versioning.md` and its section headings, which Tasks 2, 3, and 4 link to.

- [ ] **Step 1: Create the branch**

```bash
git checkout -b docs/versioning-and-deprecation-policy
```

- [ ] **Step 2: Write `docs/versioning.md`**

Required content, each item a decision the implementer must not vary:

- A one-paragraph rationale: skills are prompts, so MAJOR/MINOR/PATCH would be judgment calls on wording; a date says exactly what a user is getting.
- The scheme `YY.M.MICRO`, with the three verbatim examples from Global Constraints.
- An explicit "no zero-padding" rule naming April as the case that tempts it, and the reason: `26.04` is not valid semver and the manifest `version` field must stay semver-shaped for downstream consumers.
- A statement that the git tag and the manifest string are identical apart from the leading `v`.
- A table or list distinguishing the **tag** (one per release; cited by GitHub Releases, Zenodo, `CITATION.cff`) from the **manifest version** (one per plugin; read by Claude Code, Codex, Cursor to detect updates).
- The per-plugin rule, with the `git diff --name-only` command as the definition of "changed."
- A worked example: at `v26.11.0` all 12 plugins land on `26.11.0`; a `v26.12.0` touching three leaves nine at `26.11.0`.
- **Review Focus 1:** a new plugin's first version is the release in which it first ships.
- **Review Focus 2:** a change touching no plugin directory bumps no plugin version; the release tag still advances.
- **Review Focus 3:** micro releases follow the same per-plugin rule — `26.11.1` fixing one plugin leaves the rest at `26.11.0`.
- The manifest editing rule from Global Constraints.
- A closing pointer: CalVer does not signal breaking changes, so that job belongs to the deprecation policy. Leave the link text in place but **do not link yet** — `docs/deprecation.md` does not exist until Task 2, and Task 2 adds the link.
- No release cadence.

- [ ] **Step 3: Verify every relative link resolves**

Run:

```bash
for f in docs/versioning.md; do
  grep -oE '\]\([^)]+\)' "$f" | sed -E 's/^\]\(//; s/\)$//' | grep -vE '^(https?:|#)' | while read -r l; do
    t="${l%%#*}"; [ -z "$t" ] && continue
    [ -e "$(dirname "$f")/$t" ] || echo "BROKEN in $f: $l"
  done
done
```

Expected: no output.

- [ ] **Step 4: Verify the padding rule is stated, not just implied**

Run: `grep -n '26\.4\.0' docs/versioning.md`
Expected: at least one match. If the only examples are November dates, a future April release will get re-padded.

- [ ] **Step 5: Verify no stray zero-padded version slipped in**

Run: `grep -nE 'v?26\.0[0-9]' docs/versioning.md`
Expected: matches only inside text that explicitly labels them as wrong (the "no zero-padding" rule). Any other match is a bug.

- [ ] **Step 6: Commit**

```bash
git add docs/versioning.md
git commit -m "docs: add CalVer versioning policy"
```

---

### Task 2: Deprecation policy

**Files:**
- Create: `docs/deprecation.md`
- Modify: `docs/versioning.md` (add the link left unlinked in Task 1)

**Interfaces:**
- Consumes: `docs/versioning.md` and its definition of "release."
- Produces: `docs/deprecation.md`, linked by Tasks 3 and 4.

- [ ] **Step 1: Write `docs/deprecation.md`**

Required content:

- Scope: the user-facing identifiers — **skill, command, agent, and plugin names** — **and** a skill's **intent**, defined as the job it does and the prompts it fires on.
- The intent test, stated as a question the PR author answers: does a user's existing prompt still reach the same behavior?
  - Preserves intent: typo fixes, tightened wording, added references, corrected links.
  - Breaks intent: narrowing trigger language so it stops firing on prompts it used to catch, changing what the skill produces, dropping a capability, repurposing it to a different task.
- The two routes, with **Route 2 named the default**:
  1. *Deprecate in place* — fallback, for cases where a parallel skill would confuse users.
  2. *Ship as a new skill* — new name, old one deprecated on the same clock. Default, because users get both behaviors during the overlap and nothing breaks under them.
- The clock: no removal before **both** the next release **and** 90 days from the announcement, later governs.
- **Review Focus 5:** state explicitly that a quiet period does not unlock removal — 90 days elapsing is not sufficient on its own; a release must also have shipped.
- Required artifacts for any deprecation: a deprecation note in the affected `SKILL.md`, a `### Deprecated` entry in `CHANGELOG.md` under the plugin, and a line in the release announcement.
- **Review Focus 4:** removing a whole plugin keeps its `.claude-plugin/marketplace.json` catalog entry until the clock expires, so existing installs keep resolving.
- An **honest-limit** section, in plain words: intent preservation cannot be mechanically checked the way a rename can; it rests on the author's and reviewer's judgment, and this policy does not promise otherwise.
- A note that the author's intent assertion belongs in the PR template tracked by [#139](https://github.com/uw-ssec/savvy/issues/139).
- A visible marker that **the 90-day figure is a proposal from this PR, not a prior team decision**, inviting reviewers to push on it.

- [ ] **Step 2: Add the deprecation link to `docs/versioning.md`**

Turn the closing pointer written in Task 1 into a live relative link to `deprecation.md`.

- [ ] **Step 3: Verify both documents' links resolve**

Run the Task 1 Step 3 loop with `for f in docs/versioning.md docs/deprecation.md`.
Expected: no output.

- [ ] **Step 4: Verify the clock is stated conjunctively**

Run: `grep -ni '90' docs/deprecation.md`
Expected: at least one match whose sentence also contains "release" — the two conditions must appear together, not as alternatives.

- [ ] **Step 5: Commit**

```bash
git add docs/deprecation.md docs/versioning.md
git commit -m "docs: add deprecation policy for names and skill intent"
```

---

### Task 3: CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`

**Interfaces:**
- Consumes: `docs/versioning.md`, `docs/deprecation.md`.
- Produces: the `## [Unreleased]` heading and per-plugin subsection convention that #132 renames to `## [26.11.0]` when it cuts the tag.

- [ ] **Step 1: Write `CHANGELOG.md`**

Required content:

- Keep a Changelog 1.1.0 header, linking <https://keepachangelog.com/en/1.1.0/>.
- A line stating versions follow CalVer, linking `docs/versioning.md`.
- `## [Unreleased]` as the only release heading. **Do not add a `## [26.11.0]` section** — the tag does not exist yet and #132 owns creating it.
- Under `## [Unreleased]`, a `### <plugin-name>` subsection for each of the 12 plugins, each noting the initial tagged release. Plugin names, exactly: `ai-research-workflows`, `containerization`, `gaia-data-downloader`, `holoviz-visualization`, `project-management`, `research-software-design`, `scientific-domain-applications`, `scientific-python-development`, `supply-chain-security`, `uiux-design-team`, `zarr-chunk-optimization`, `zarr-data-format`.
- A short "How to add an entry" note: add under `## [Unreleased]`, under your plugin's `###` subsection, using Keep a Changelog's categories (Added, Changed, Deprecated, Removed, Fixed, Security), and pointing `Deprecated` entries at `docs/deprecation.md`.
- Do **not** reconstruct history prior to this release.

- [ ] **Step 2: Verify all 12 plugins are present and spelled as their directories**

Run:

```bash
for p in $(ls -d plugins/*/ community-plugins/*/ | xargs -n1 basename); do
  grep -q "^### $p$" CHANGELOG.md || echo "MISSING: $p"
done
```

Expected: no output.

- [ ] **Step 3: Verify no premature release section**

Run: `grep -nE '^## \[26\.' CHANGELOG.md`
Expected: no output.

- [ ] **Step 4: Verify links resolve**

Run the Task 1 Step 3 loop with `for f in CHANGELOG.md`.
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG following Keep a Changelog"
```

---

### Task 4: Wire CONTRIBUTING.md and README.md

**Files:**
- Modify: `CONTRIBUTING.md` — new section between `## 📦 Plugin Manifests and Other Clients` (`CONTRIBUTING.md:132`) and `## 📊 Evaluating Skills` (`CONTRIBUTING.md:156`); PR checklist items at `CONTRIBUTING.md:113-120`
- Modify: `README.md` — `## Documentation` list at `README.md:411-413`

**Interfaces:**
- Consumes: `docs/versioning.md`, `docs/deprecation.md`, `CHANGELOG.md`.

- [ ] **Step 1: Add the policy section to `CONTRIBUTING.md`**

A `## 🏷️ Versioning and Deprecation` section, placed between the two sections named above. Three or four sentences: releases use CalVer (link `docs/versioning.md`), renames and intent-breaking skill changes follow the deprecation policy (link `docs/deprecation.md`), every PR adds a `CHANGELOG.md` entry under `## [Unreleased]`. Match the existing emoji-heading style.

- [ ] **Step 2: Add two lines to the PR checklist**

Append to the existing list at `CONTRIBUTING.md:113-120`, matching its `- [ ]` style:

```markdown
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]` for each plugin you changed
- [ ] Any rename, removal, or intent-breaking skill change follows [the deprecation policy](docs/deprecation.md)
```

- [ ] **Step 3: Add the policies to the README Documentation list**

Two bullets in `## Documentation`, matching the existing `- [Name](path) - description` format, for `docs/versioning.md` and `docs/deprecation.md`.

> Reviewer's call: this step is discoverability, not an acceptance criterion of #130. Drop it if a reviewer prefers the README untouched.

- [ ] **Step 4: Verify both policies are reachable from CONTRIBUTING.md**

Run: `grep -c 'docs/versioning.md\|docs/deprecation.md' CONTRIBUTING.md`
Expected: `2` or more.

- [ ] **Step 5: Verify every changed document's links resolve**

Run the Task 1 Step 3 loop with `for f in CHANGELOG.md docs/versioning.md docs/deprecation.md CONTRIBUTING.md README.md`.
Expected: no output.

- [ ] **Step 6: Verify the repo gate still passes**

Run: `pixi run plugins-check`
Expected: exit 0. Nothing in this plan touches a manifest, so a failure here means something unrelated broke — stop and investigate rather than editing a manifest to make it pass.

- [ ] **Step 7: Commit**

```bash
git add CONTRIBUTING.md README.md
git commit -m "docs: link versioning, deprecation, and changelog from contributor docs"
```

---

### Task 5: Record the superseded acceptance criteria

**Files:** none — this task acts on GitHub.

- [ ] **Step 1: Confirm with the human partner before posting**

This writes to a public repository. Show them the comment text and the PR body and wait for an explicit go-ahead.

- [ ] **Step 2: Comment on #130**

State that the body's per-plugin semver criteria are superseded by the CalVer comments, and map each original acceptance criterion to what this PR delivers. Do not edit the issue body — a comment preserves the record.

- [ ] **Step 3: Open the PR**

Body must call out, for reviewers:
- the 90-day floor as a proposal from this PR, not a team decision;
- the choice of two separate policy files over one;
- the `rse-plugins` → `savvy` naming staleness, noted but deliberately not fixed;
- that version bumps and `plugins-sync` are deliberately left to #132.

End the PR description with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## Verification summary

| Acceptance criterion (#130) | Delivered by |
|---|---|
| CHANGELOG.md follows Keep a Changelog, entries per plugin | Task 3 |
| A versioning policy with agreed examples | Task 1 (CalVer, superseding the body's semver examples) |
| A deprecation policy: notice period, note in the skill, removal announcement | Task 2 |
| CONTRIBUTING.md links the policies and asks PRs to update the changelog | Task 4 |
