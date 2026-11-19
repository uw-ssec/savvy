---
name: supply-chain-threat-awareness
description: Use when running a supply-chain posture review or security audit of a repo, or when someone asks "are we exposed or affected?" about an attack campaign such as Shai-Hulud, TeamPCP, the axios compromise or the LiteLLM .pth backdoor. Also use when reviewing GitHub Actions for mutable action tags, or a project for npm install scripts, lockfile hygiene or dependency cooldown. Not for generating or signing SBOMs, or for handling a confirmed compromise.
metadata:
  references: references/campaigns/shai-hulud.md references/campaigns/teampcp.md references/campaigns/axios.md references/campaigns/litellm-pth.md references/posture-report-template.md references/audit-commands.md
---

# Supply Chain Threat Awareness

## Overview

Recent campaigns shipped malware under trusted names: hijacked maintainer accounts, stolen publish tokens, force-pushed action tags. No CVE existed while the bad versions were live, so a clean scan proves little. This audit checks the five weaknesses they used and ties each finding to a campaign.

## When to Use

- A posture review or security audit of a repo, or "are we exposed to <campaign>?"
- Reviewing workflows, manifests (`package.json`, `pyproject.toml`, `pixi.toml`) or lockfiles for supply-chain risk.

Not for: confirmed compromises (`supply-chain-incident-response`), SBOMs and signing (`supply-chain-sbom-provenance`), or rewriting workflows (`supply-chain-hardened-ci-cd`).

## Campaigns (observed 2025–2026, verified 2026-11)

Read a campaign file only when a finding matches.

- **Shai-Hulud** (npm, Sep 2025; second wave Nov 2025): an install-script worm; each stolen npm token published infected versions of the victim's other packages. `references/campaigns/shai-hulud.md`
- **TeamPCP** (Mar–Apr 2026): force-pushed Trivy and Checkmarx action tags to steal CI secrets; malicious LiteLLM, Telnyx, Bitwarden CLI and SAP CAP releases followed. `references/campaigns/teampcp.md`
- **axios** (npm, Mar 2026): a hijacked maintainer account published 1.14.1 and 0.30.4, adding a dependency whose `postinstall` dropped a remote access trojan. `references/campaigns/axios.md`
- **LiteLLM `.pth`** (PyPI, Mar 2026, part of TeamPCP): 1.82.8 shipped `litellm_init.pth`, which runs on every Python start. `references/campaigns/litellm-pth.md`

## Quick Reference

Run all five steps, then report. FAILs in steps 1–3 are critical. Commands and PASS/FAIL details: `references/audit-commands.md`.

The `/supply-chain-*` commands below load only in clients that load plugin commands. If one is not in your available commands, report the fix itself, without the command name.

| Step | FAIL when | Fix | Campaigns |
|---|---|---|---|
| 1. Lockfiles | An ecosystem has no committed lockfile, or CI installs without it (`npm install`; `pixi install` or `uv sync` without `--locked`) | `npm ci`, `uv sync --locked`, `pixi install --locked`; `/supply-chain-lockfile-check` | all |
| 2. Action pinning | Any `uses:` ref is not a full 40-character SHA, a local `./` path or an image digest | Pin each ref to its full commit SHA with a `# vX.Y.Z` comment; `/supply-chain-pin-actions` | TeamPCP |
| 3. Install-time code | A CI npm install runs scripts, or a lifecycle script is unreviewed | `npm ci --ignore-scripts`. For `.pth` files, use the PyPI `.pth` check in `supply-chain-ecosystem-quirks`. | Shai-Hulud, axios, LiteLLM |
| 4. Cooldown | A newly adopted version was younger than the cooldown (7 days unless the project sets one) when merged | Dependabot `cooldown`, Renovate `minimumReleaseAge` | all |
| 5. Provenance | Releases have no SBOM or signature | `supply-chain-sbom-provenance` | none |

## Output: Posture Report

Fill in `references/posture-report-template.md`. Each finding gives the campaign, `file:line`, blast radius and fix.

## Common Mistakes

- **Finding mutable refs with `@[^a-f0-9]`.** It misses refs starting with a hex character (`@dev`, `@beta`, trivy-action's `@0.34.2`) and skips `.yaml` files. Exclude only full SHAs and `./` paths.
- **Measuring cooldown as time between lockfile commits.** Commits ten days apart can adopt a 90-minute-old release. Compare each version's publish and merge times.
- **Flagging every `.pth` line that starts with `import`.** setuptools ships such a file (`distutils-precedence.pth`).
- **Accepting `pixi install` or `uv sync --frozen` as locked installs.** `pixi install` rewrites a stale `pixi.lock`; `--frozen` skips the lock-versus-manifest check.
