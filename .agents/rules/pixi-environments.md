# Pixi Environments & Dependencies

**Load when:** setting up the repo, running any command, adding or changing a
dependency, or editing `pixi.toml`.

## Pixi Overview

This repository uses **Pixi** for its tooling environments. See
https://pixi.sh/latest/llms-full.txt for details.

**ALWAYS use Pixi commands — never use conda, pip, or venv directly.** The CI
scripts need no system Python; the `ci` environment locks Python and every
checker.

## Environment Setup

```bash
pixi install            # default environment (okf CLI, zarr)
pixi install -e ci      # CI tooling; pixi also installs it on first `pixi run <ci task>`
```

`pixi install` is idempotent and safe to run repeatedly.

## Available Environments

1. **`default`** (features: `okf`)

   - `zarr` (added with the zarr-chunk-optimization plugin)
   - `okf-agent-memory`, which provides the `okf` CLI for `knowledge/`

2. **`ci`** (features: `ci`, no default feature)
   - Python 3.12, PyYAML, pytest, check-jsonschema, lychee, SkillEvaluator
   - Kept separate so CI does not pull in zarr or okf

`evals/dokimi-pilot/` has its own `pixi.toml` and lock; it is not part of the
root workspace.

## Available Pixi Tasks

All tasks live in the `ci` feature. Pixi picks the environment automatically, so
`pixi run <task>` works without `-e ci`. Run `pixi task list` for the full list.

| Task                  | What it does                                                                     |
| --------------------- | -------------------------------------------------------------------------------- |
| `check-all`           | `plugins-check` + `catalog-check` + `test-scripts` — the minimum offline gate    |
| `plugins-sync`        | Regenerate the generated manifests and marketplaces from the sources             |
| `plugins-check`       | Check manifests, skills, and relative links (CI gate)                            |
| `plugins-check-claude` | `plugins-check` plus `claude plugin validate --strict` (needs `claude` on PATH)  |
| `catalog-sync`        | Regenerate `docs/catalog.md`                                                     |
| `catalog-check`       | Check `docs/catalog.md` is current and every skill has an entry (CI gate)        |
| `test-scripts`        | Run the CI script tests                                                          |
| `links-check`         | Check external URLs with lychee (needs network; set `GITHUB_TOKEN`)              |
| `skill-quality-check` | SkillEvaluator on one skill: `pixi run -e ci skill-quality-check plugins/<p>/skills/<s>` |

## Adding Dependencies

```bash
pixi add --feature ci <package>      # repository tooling
pixi add --feature okf <package>     # only if it serves the okf workflow
pixi install
```

Pin CI tooling exactly (`"6.0.3.*"`), as the existing `ci` entries do, so a
checker can't change behavior under a PR. Adding a dependency needs
justification — see [contribution-discipline.md](contribution-discipline.md).

Channels: `conda-forge` only. Do not add others.

## OKF Agent Memory

`okf-agent-memory` is supplied by the `okf` feature. The package installs a
binary named **`okf`**:

```bash
pixi run okf version   # 0.6.1 (OKF v0.2 specification) or higher
pixi run okf --help
```

The `okf-memory` skill (`.agents/skills/okf-memory/`) says how to use it.
