---
name: supply-chain-ecosystem-quirks
description: Use when reviewing ecosystem-specific supply-chain settings in npm, PyPI, conda/pixi, cargo or Go projects, such as .npmrc and ignore-scripts, setup.py, backend-path or --no-build-isolation, Python .pth startup files, conda channels in .condarc, pixi.toml or environment.yml, Cargo.toml with build.rs or cargo --locked, and go.mod with GOPROXY or GOSUMDB.
metadata:
  references: references/npm-quirks.md references/pypi-quirks.md references/conda-pixi-quirks.md references/cargo-go-quirks.md
  scripts: scripts/quick-check.sh
---

# Supply Chain Ecosystem Quirks

## Overview

Each package manager has its own install-time execution paths and config knobs, which decide whether the general controls from `supply-chain-dependency-security` and `supply-chain-hardened-ci-cd` hold.

## When to Use

- A review touches a manifest or config in the table below, and the answer depends on the package manager.
- Another skill asks for the PyPI `.pth` check.

Not for: a known compromise (`supply-chain-incident-response`), campaign exposure (`supply-chain-threat-awareness`), or release workflow hardening (`supply-chain-hardened-ci-cd`).

## Quick Reference

1. Run the script. It prints `<ecosystem> FAIL|WARN|INFO: <message>`, with a `detected` line naming each ecosystem's reference, and exits 1 on any FAIL.
2. For each FAIL or WARN, and for any ecosystem the user wants reviewed in depth, read only the matching `references/<eco>-quirks.md`.
3. Write the report below.

| Script | Purpose |
|--------|---------|
| `bash scripts/quick-check.sh <project-dir>` | All checks for the detected ecosystems |
| `bash scripts/quick-check.sh --pth-only [--env <env-prefix>] <project-dir>` | The PyPI `.pth` check alone: standard startup files are INFO, unknown code-executing `.pth`/`.start` files FAIL. Rules: ".pth Check (Canonical)" in `references/pypi-quirks.md` |

| Ecosystem | Trigger files | Reference |
|-----------|---------------|-----------|
| npm / yarn / pnpm | `package.json`, `.npmrc`, lockfiles | `references/npm-quirks.md` |
| PyPI / pip / uv / poetry | `pyproject.toml`, `setup.py`, `requirements.txt`, `uv.lock`, `poetry.lock` | `references/pypi-quirks.md` |
| conda / pixi | `pixi.toml`, `environment.yml`, `conda-lock.yml`, `.condarc` | `references/conda-pixi-quirks.md` |
| cargo | `Cargo.toml`, `.cargo/config.toml` | `references/cargo-go-quirks.md` |
| Go | `go.mod`, `GOPROXY` env | `references/cargo-go-quirks.md` |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| FAIL on every `.pth` line starting with `import` | setuptools, `uv venv` and editable installs write them; match name and exact content |
| Finding site-packages with `python -c "import site..."` | That runs every `.pth`, and a missing `python` looks like a PASS; the script uses `-I -S` |
| `grep -A 5 '^channels:' pixi.toml` | Pixi channels are a TOML array; check both formats |
| npm FAIL for a missing `.npmrc` when CI runs `npm ci --ignore-scripts` | Either control passes |
| Demanding `package-lock.json` from pnpm or Yarn projects | Accept their lockfile |
| WARN that `go build` lacks `-mod=readonly` | Default since Go 1.16; flag `-mod=mod` |
| `--frozen` as the CI lock check for pixi or uv | `--frozen` skips the check; use `--locked` |

## Output: Ecosystem Quirks Report

Cite `file:line` (or `absent`) for every result and a concrete command, config key or skill for every fix.

```markdown
## Ecosystem Quirks Posture: <project>

### Ecosystems Detected
| Ecosystem | Evidence (trigger file) | Reference read |

### Findings
| Ecosystem | Quirk / control | PASS/WARN/FAIL | Evidence (file:line) | Fix |

### Conflicts with General Guidance
The ecosystem quirk wins. Example: with `ignore-scripts=true` in `.npmrc`, `npm rebuild <package>` succeeds but runs nothing; use `npm rebuild <package> --ignore-scripts=false`.

### Top Priority Actions
1. <highest-impact runnable fix>
```

If the script detects nothing: `No supported package-manager manifests found; this skill does not apply.`
