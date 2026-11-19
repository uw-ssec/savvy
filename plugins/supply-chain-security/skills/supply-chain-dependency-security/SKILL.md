---
name: supply-chain-dependency-security
description: Use when reviewing a dependency update, a Dependabot or Renovate PR, or a lockfile (package-lock.json, yarn.lock, pnpm-lock.yaml, uv.lock, poetry.lock, pixi.lock, conda-lock.yml, requirements.txt); when adding a new package; when a postinstall script, `--ignore-scripts` or a `.pth` file comes up; or when judging whether a newly published version could come from a maintainer account takeover.
---

# Supply Chain Dependency Security

Keeps malicious releases out of dependency updates and CI installs.

**Core principle:** a clean CVE scan says nothing about a version published hours ago: no advisory exists yet.

Observed 2025–2026, verified 2026-11: major incidents were maintainer account takeovers, not typosquats. Campaigns: `supply-chain-threat-awareness`.

## When to Use

- A Dependabot or Renovate PR, any lockfile diff, or a new package
- CI fails under `--ignore-scripts`

**Not for** workflow hardening (`supply-chain-hardened-ci-cd`). If a dependency is compromised:

**REQUIRED SUB-SKILL:** Use supply-chain-security:supply-chain-incident-response

## Rules

1. **Lockfile only.** Commit it. CI's install command must fail on a stale lockfile (table below). No `*` or `latest` in manifests.
2. **Install scripts off.** Never drop `--ignore-scripts`, even once. Rebuild only what needs it:

   ```bash
   npm ci --ignore-scripts
   npm rebuild <package>
   ```

   npm 12+: approve it first (`npm install-scripts approve <package>`, commit `package.json`).
3. **7-day cooldown.** Nothing younger merges. Cooldown settings filter resolution, not locked versions. Check the age of every version a lockfile diff adds: `npm view <package> time`, or the cooldown check in `supply-chain-threat-awareness`.
4. **Check the publisher.** Compare with earlier releases (`npm view <package>@<version> _npmUser`), run `npm audit signatures`, read `npm diff --diff=<package>@<old> --diff=<package>@<new>`. A first-time publisher on an established package is the takeover pattern: hold the version.
5. **`.pth` files:** use the PyPI `.pth` check in `supply-chain-ecosystem-quirks`.
6. **Findings:** class, `<package>@<version>`, advisory or campaign, install-time reach, fix.

## Quick Reference

| Tool | CI install | Resolver cooldown |
|---|---|---|
| npm | `npm ci --ignore-scripts` | `.npmrc`: `min-release-age=7` (11.10+) |
| pnpm | `pnpm install --frozen-lockfile` | `pnpm-workspace.yaml`: `minimumReleaseAge: 10080` (minutes; 10.16+) |
| Yarn | `yarn install --immutable` with `enableScripts: false` (default from 4.14); v1: `--frozen-lockfile --ignore-scripts` | `.yarnrc.yml`: `npmMinimalAgeGate: 10080` (minutes; 4.10+) |
| uv | `uv sync --locked` | `[tool.uv]`: `exclude-newer = "7 days"` (0.9.17+) |
| Poetry | `poetry install` (refuses a stale lock) | `poetry config --local solver.min-release-age 7` (2.4+) |
| pip | `pip install --require-hashes -r requirements.txt` | `--uploaded-prior-to P7D` (26.1+) |
| pixi | `pixi install --locked` | `[workspace]`: `exclude-newer = "7d"` (0.67+) |
| conda-lock | `conda-lock install -n <env> conda-lock.yml` | none |

Bots: Dependabot `cooldown:` with `default-days: 7`; Renovate `"minimumReleaseAge": "7 days"`. Neither delays security updates.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Only for the demo build", "temporary" | One build with scripts on is all a malicious `postinstall` needs. |
| "`--ignore-scripts` breaks the build" | Only packages needing an install step break; rebuild those. |
| "It's a trusted, popular package" | Takeovers target trusted packages; popularity is the payoff. |

## Red Flags

- Removing or bypassing `--ignore-scripts` for any build
- A version under 7 days old, or from a first-time publisher

**Either one: keep the control, hold the version.**

## Common Mistakes

- **`pixi install` in CI:** rewrites `pixi.lock` when the manifest changed; `--frozen` skips the check. Use `--locked`. Same for `uv sync --frozen`.
- **`ignore-scripts=true` in `.npmrc`:** `npm rebuild <package>` silently runs nothing. Add `--ignore-scripts=false` to that rebuild.
