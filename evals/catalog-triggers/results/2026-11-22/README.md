# Trigger fixture results, 2026-11-22

Every skill's [trigger fixture](../../fixtures/) run in headless Claude Code
2.1.330 with only savvy's 12 plugins loaded (`--setting-sources project`, no
user settings, hooks or MCP servers), through the LLMoxie LiteLLM gateway.
Each of the 405 prompts ran 3 times per model: 1,215 runs per model.

- A `fire` run passes when the first skill invoked is the target skill, a
  command in `DELEGATES` that only hands off to it, or the target after a
  `ROUTERS` skill.
- A `no-fire` run passes when the target is not invoked.
- A case passes at 2 of 3 runs; a skill passes when every case passes.
- Per-skill tables: [Haiku 5.5](ssec-claude-haiku-5-5.md),
  [Sonnet 5.5](ssec-claude-sonnet-5-5.md), [Opus 5.5](ssec-claude-opus-5-5.md).
  Raw runs are in the matching `.jsonl` files.

The six uiux fixtures whose neighbor cases were corrected
(`information-architecture`, `typography-systems`, `usability-evaluation`,
`user-journey-mapping`, `user-research`, `visual-design`) were rerun with the
corrected fixtures, and their earlier runs were replaced.

## Summary

| Model | Skills passing every case | `fire` runs that loaded the skill | `obvious` | `tired` | False triggers on `no-fire` runs |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ssec-claude-haiku-5-5` | 1/76 | 34/729 (4.7%) | 27/456 (5.9%) | 7/273 (2.6%) | 0/486 |
| `ssec-claude-sonnet-5-5` | 6/76 | 153/729 (21.0%) | 111/456 (24.3%) | 42/273 (15.4%) | 0/486 |
| `ssec-claude-opus-5-5` | 12/76 | 304/729 (41.7%) | 241/456 (52.9%) | 63/273 (23.1%) | 0/486 |

## Activation by plugin (`fire` runs that loaded the skill)

| Plugin | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
| --- | ---: | ---: | ---: |
| ai-research-workflows | 7/90 | 43/90 | 72/90 |
| containerization | 0/78 | 17/78 | 38/78 |
| gaia-data-downloader | 1/12 | 11/12 | 12/12 |
| holoviz-visualization | 14/81 | 17/81 | 43/81 |
| project-management | 0/18 | 3/18 | 6/18 |
| research-software-design | 2/9 | 3/9 | 8/9 |
| scientific-domain-applications | 0/21 | 0/21 | 0/21 |
| scientific-python-development | 0/51 | 6/51 | 17/51 |
| supply-chain-security | 10/63 | 22/63 | 39/63 |
| uiux-design-team | 0/213 | 18/213 | 39/213 |
| zarr-chunk-optimization | 0/48 | 13/48 | 28/48 |
| zarr-data-format | 0/45 | 0/45 | 2/45 |

## What the runs show

- **Under-triggering, not misrouting.** No skill fired on a `no-fire` prompt
  on any model (0 of 1,458 runs). Of all `fire` runs that missed, the model
  usually loaded no skill at all and answered or started working on its own.
  Only 30 of the 1,696 misses across the three models loaded a different skill or command.
- **Activation depends on the model more than on the description.** The same
  prompts load a skill about 9 times as often on Opus as on Haiku.
- **`tired` phrasing loads less often than `obvious` phrasing** on every model.
- **22 skills never fired on any model:** `containerization/dockerfile-patterns`,
  `holoviz-visualization/data-visualization`, both
  `scientific-domain-applications` skills,
  `scientific-python-development/python-testing`,
  `supply-chain-security/supply-chain-threat-awareness`, 12 `uiux-design-team`
  skills (`ab-testing-strategy`, `design-handoff`, `design-tokens`,
  `frontend-components`, `grid-layout-systems`, `responsive-design`,
  `typography-systems`, `usability-evaluation`, `user-research`, `ux-writing`,
  `visual-design`, `wireframing`), and four `zarr-data-format` skills
  (`compression-codecs`, `data-migration`, `zarr-fundamentals`,
  `zarr-xarray-integration`).
- **What took requests instead, when something did:**
  - Commands that run a full workflow built on the skill:
    `/supply-chain-audit` (9 runs meant for `supply-chain-threat-awareness`),
    `/map-journey` (6, `user-journey-mapping`), `/create-design-system` (1).
    The test counts these as misses, as before; only commands that do nothing
    but hand off (`DELEGATES`) count as the skill.
  - Sibling skills: `supply-chain-incident-response` (4, threat-awareness),
    `information-architecture` (3, `wireframing`),
    `supply-chain-ecosystem-quirks` (1, dependency-security).
  - **A skill built into Claude Code**, `dataviz`, took requests meant for
    `holoviz-visualization/data-visualization` (4) and
    `uiux-design-team/grid-layout-systems` (2). Users who install savvy will
    have it too, so it is a fair competitor.

## Compared with SkillEvaluator Tier 2 (#235)

Tier 2's embedding overlap (`nvidia/nemotron-3-embed-1b`, run locally) found
no description pairs at or above 0.75, and 28 pairs of full skill bodies, one
of them high: `data-visualization` and `plotting-fundamentals` (0.902). None
of the 28 pairs appears as a confusion here. `data-visualization` never fired
at all, and the confusions that did happen (threat-awareness and
incident-response, wireframing and information-architecture) are not among
Tier 2's top pairs, except supply-chain-incident-response and
supply-chain-threat-awareness (0.763). Static overlap does not predict live
routing; the #230 pilot found the same for static discoverability scores.
