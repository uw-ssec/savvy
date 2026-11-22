# Trigger fixture results, 2026-11-22

Every skill's [trigger fixture](../../fixtures/) run in headless Claude Code
2.1.330 with only savvy's 12 plugins loaded (`--setting-sources project`, no
user settings, hooks or MCP servers), through the LLMoxie LiteLLM gateway.
Each of the 405 prompts ran 3 times per model: 1,215 runs per model. No run
failed on an API or CLI error.

- A `fire` run passes when the first skill invoked is the target skill, a
  command in `DELEGATES` that only hands off to it, or the target after a
  `ROUTERS` skill.
- A `no-fire` run passes when the target is not invoked.
- A case passes at 2 of 3 runs; a skill passes when every case passes.
- Per-skill tables: [Haiku 5.5](ssec-claude-haiku-5-5.md),
  [Sonnet 5.5](ssec-claude-sonnet-5-5.md), [Opus 5.5](ssec-claude-opus-5-5.md).
  Raw runs are in the matching `.jsonl` files.

## Summary

| Model | Skills passing every case | `fire` runs that loaded the skill | `obvious` | `tired` | `no-fire` runs that loaded the target |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ssec-claude-haiku-5-5` | 1/76 | 40/729 (5.5%) | 32/456 (7.0%) | 8/273 (2.9%) | 0/486 |
| `ssec-claude-sonnet-5-5` | 2/76 | 145/729 (19.9%) | 113/456 (24.8%) | 32/273 (11.7%) | 0/486 |
| `ssec-claude-opus-5-5` | 9/76 | 281/729 (38.5%) | 222/456 (48.7%) | 59/273 (21.6%) | 0/486 |

## Activation by plugin (`fire` runs that loaded the skill)

| Plugin | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 |
| --- | ---: | ---: | ---: |
| ai-research-workflows | 7/90 | 43/90 | 71/90 |
| containerization | 0/78 | 13/78 | 32/78 |
| gaia-data-downloader | 1/12 | 10/12 | 12/12 |
| holoviz-visualization | 13/81 | 16/81 | 32/81 |
| project-management | 1/18 | 2/18 | 6/18 |
| research-software-design | 2/9 | 3/9 | 8/9 |
| scientific-domain-applications | 0/21 | 0/21 | 0/21 |
| scientific-python-development | 1/51 | 8/51 | 13/51 |
| supply-chain-security | 13/63 | 19/63 | 40/63 |
| uiux-design-team | 2/213 | 18/213 | 37/213 |
| zarr-chunk-optimization | 0/48 | 13/48 | 29/48 |
| zarr-data-format | 0/45 | 0/45 | 1/45 |

## What the runs show

- **Under-triggering, not misrouting.** The target skill never loaded on a
  `no-fire` prompt on any model (0 of 1,458 runs). Other skills or commands
  did load on some of those prompts (43, 108 and 196 runs on Haiku, Sonnet
  and Opus), usually the neighbor's owner. Of the 1,721 `fire` runs that
  missed, 30 loaded a different skill or command; in the rest the model
  loaded no skill at all and answered or started work on its own.
- **Activation depends on the model more than on the description.** The same
  prompts load a skill about 7 times as often on Opus as on Haiku.
- **`tired` phrasing loads less often than `obvious` phrasing** on every
  model, about half as often.
- **19 skills never fired on any model:** `containerization/dockerfile-patterns`,
  both `scientific-domain-applications` skills,
  `scientific-python-development/python-testing`,
  `supply-chain-security/supply-chain-threat-awareness`, 10 `uiux-design-team`
  skills (`ab-testing-strategy`, `design-tokens`, `frontend-components`,
  `grid-layout-systems`, `responsive-design`, `typography-systems`,
  `usability-evaluation`, `user-research`, `ux-writing`, `wireframing`), and
  four `zarr-data-format` skills (`compression-codecs`, `data-migration`,
  `zarr-fundamentals`, `zarr-xarray-integration`).
- **What took requests instead, when something did:**
  - Commands that run a full workflow built on the skill:
    `/supply-chain-audit` (9 runs meant for `supply-chain-threat-awareness`),
    `/map-journey` (6, `user-journey-mapping`), `/create-design-system` (2,
    `design-system-creation`). The test counts these as misses; only commands
    that do nothing but hand off (`DELEGATES`) count as the skill.
  - Sibling skills: `supply-chain-incident-response` (6, threat-awareness),
    `supply-chain-dependency-security` (1, ecosystem-quirks),
    `information-architecture` (1, `wireframing`).
  - **A skill built into Claude Code**, `dataviz`, took requests meant for
    `holoviz-visualization/data-visualization` (4) and
    `uiux-design-team/grid-layout-systems` (1). Users who install savvy will
    have it too, so it is a fair competitor.

## Compared with SkillEvaluator Tier 2 (#235)

Tier 2's embedding overlap (`nvidia/nemotron-3-embed-1b`, run locally) found
no description pairs at or above 0.75, and 28 pairs of full skill bodies, one
of them high: `data-visualization` and `plotting-fundamentals` (0.902). Only
one of those pairs shows up as a confusion here:
`supply-chain-incident-response` and `supply-chain-threat-awareness` (0.763).
`data-visualization` lost requests to `dataviz`, not to `plotting-fundamentals`,
and the other confusions are with commands, which Tier 2 doesn't compare.
Static overlap does not predict live routing; the #230 pilot found the same
for static discoverability scores.
