# Versioning Policy

This repository uses **Calendar Versioning (CalVer)**, in the [Ubuntu style](https://calver.org/#ubuntu).

## Why CalVer and not semver

Skills and agents are prompts. A reworded sentence can change how a skill behaves, and a sentence that looks substantial can change nothing at all. Sorting those into MAJOR, MINOR and PATCH would be a judgment call on almost every pull request, and two reasonable maintainers would sort them differently.

A date does not require that judgment. `26.11.0` tells a user exactly what they have: the November 2026 release. What CalVer cannot tell them is that something broke — so that job belongs entirely to the deprecation policy (see [Breaking changes](#breaking-changes) below).

## The scheme

Releases are numbered `YY.M.MICRO`:

| Example | Meaning |
| --- | --- |
| `v26.11.0` | The November 2026 release |
| `v26.11.1` | A fix shipped between releases, Ubuntu point-release style |
| `v26.4.0` | The April 2026 release |

**MICRO counts additional releases within the same month, starting at 0.** The first release in a month is `.0`, the next is `.1`, and so on. Usually that later release is a fix shipped between months — the Ubuntu point-release case — but the number is mechanical, so a second feature release in the same month is simply the next MICRO rather than a problem.

No cadence is fixed. Releases happen when there is something to release.

### No zero-padding

Write `v26.4.0`, never `v26.04.0`.

Ubuntu's own `YY.0M` format pads single-digit months, and April is where the temptation bites. Don't. Semantic versioning forbids leading zeros in a numeric identifier, so `26.04` is not a valid version string, and the `version` field in every plugin manifest has to stay semver-shaped for the tools that read it.

Dropping the padding everywhere keeps one rule with no translation step: **the git tag and the manifest version are the same string, apart from the tag's leading `v`.** Tag `v26.11.0` means manifest `"version": "26.11.0"`.

## Tags and manifest versions are different things

| | Git tag | Manifest `version` |
| --- | --- | --- |
| How many | One per release | One per plugin |
| Lives in | A git ref | `<plugin>/plugin.json` |
| Read by | People, GitHub Releases, Zenodo, `CITATION.cff` | Plugin clients — Claude Code, Codex, Cursor |
| Answers | "What shipped in November?" | "Is my copy of *this plugin* up to date?" |

## Per-plugin versions

**A plugin's manifest version is the release in which that plugin last changed.** Plugins that did not change keep their older version — that is how a user sees which parts of the repository actually moved.

"Changed" is decided mechanically, not by judgment:

```bash
pixi run -e ci python .github/scripts/skill_trust.py changed-plugins <previous-tag>
```

If that lists a plugin, it changed and its version becomes the new release. A plugin it does not list keeps its version. For the first release there is no previous tag: skip the command, and every plugin takes the new version.

The command prints every plugin directory (`plugins/<name>` and `community-plugins/<name>`) with at least one changed path outside a skill's evidence files: `skills/<skill>/evals/`, `skills/<skill>/BENCHMARK.md`, and `skills/<skill>/skill-card.md`. Evidence describes how a skill was tested; it does not change what the skill does, so a pull request that only adds or refreshes it does not move the plugin's version. The same file elsewhere (for example `skills/<skill>/references/BENCHMARK.md`) is ordinary content and does count.

**Order matters.** Compute the changed set **before editing any manifest**, and commit the version bumps **before cutting the tag**. A version bump is itself a write inside the plugin's directory, so computing the set after bumping — or tagging before the bumps land — marks every plugin as changed at every release, destroying the signal this rule exists to provide.

### Worked example

At `v26.11.0`, the first tagged release, every plugin lands on `26.11.0`.

Say `v26.12.0` then changes three plugins. Those three become `26.12.0`. The other nine stay at `26.11.0`, and a user comparing their installed versions can see at a glance that nine of them did not move.

### Cases this covers

- **A new plugin** takes the version of the release in which it first ships. It does not start at `0.1.0`.
- **A change that touches no plugin directory** — a README, a workflow, a file under `docs/` — bumps no plugin version at all. The release tag still advances; the manifests do not.
- **Micro releases follow the same rule.** If `v26.11.1` fixes one plugin, that plugin becomes `26.11.1` and every other plugin stays at `26.11.0`.

### Where to edit a version

Edit `<plugin>/plugin.json` and nothing else. Then run:

```bash
pixi run plugins-sync
```

That regenerates `<plugin>/.claude-plugin/plugin.json`, the entry in `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, and `.cursor-plugin/marketplace.json`. CI runs `pixi run plugins-check`, which fails on any drift between the source manifest and the generated ones.

## Breaking changes

CalVer carries no signal for a breaking change — `26.12.0` looks exactly like `26.11.0` whether a skill was renamed or a typo was fixed. Renames, removals, and changes to what a skill actually does are therefore governed by the [deprecation policy](deprecation.md), which defines the notice a user is owed before anything they depend on disappears.

## See also

- [Contributing Guidelines](../CONTRIBUTING.md)
- [`CHANGELOG.md`](../CHANGELOG.md), which records what changed in each release in the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format
