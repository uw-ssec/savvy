---
name: supply-chain-hardened-ci-cd
description: Use when writing, reviewing or hardening GitHub Actions workflows in .github/workflows, especially a release or publish workflow for PyPI or npm publishing; when a `uses:` line needs pinning to a commit SHA; when a workflow uses pull_request_target, broad workflow permissions, GITHUB_TOKEN scopes or secrets in CI; when setting up OIDC trusted publishing or harden-runner; or when fixing zizmor findings.
metadata:
  references: references/hardening-patterns.md
---

# Supply Chain Hardened CI/CD

Hardens GitHub Actions workflows against hijacked actions and stolen publish credentials.

**Core principle:** every `uses:` step is third-party code running with your token. Pin it, scope its permissions, and keep publish credentials out of jobs that build or run untrusted code.

TeamPCP (March 2026) hijacked release tags on Trivy, Checkmarx, LiteLLM, Bitwarden CLI and SAP CAP; workflows on tags like `@v3` ran the attacker's commit.

## When to Use

Writing or reviewing any `.github/workflows/*.yml`, above all release jobs; adding a `uses:` step, secret or `pull_request_target` trigger; zizmor output. Not for lockfiles (`supply-chain-dependency-security`), SBOMs or signing (`supply-chain-sbom-provenance`), or a live compromise (`supply-chain-incident-response`).

## Quick Reference

| Rule | Violation | Fix |
|---|---|---|
| Pin to a commit SHA | `@v4`, `@main`, `@release/v1` | `@<40-char-sha>  # vX.Y.Z` |
| Deny by default | `write-all`, or no top-level `permissions:` | `permissions: {}`, then per-job grants |
| No Pwn Request | `pull_request_target` plus checkout of PR code | `pull_request`: forks get no secrets, read-only token by default |
| Split build and publish | One job builds and uploads | Artifact handoff; publish job `needs: build` |
| OIDC trusted publishing | `password:`, `PYPI_TOKEN`, `NPM_TOKEN` | PyPI/npm trusted publisher; `id-token: write` in publish job only; delete the secret |
| Gate publishing | Publish job without `environment:` | `environment:` with required reviewers |
| No install scripts | Bare `npm ci`, `npm publish`, `pip install`, `python -m build` | `--ignore-scripts`; `PIP_ONLY_BINARY=:all:` or `uv sync --locked --no-build` |
| Limit egress | Release job without egress control | `step-security/harden-runner` first: `egress-policy: audit`, then `block` |
| Automated check | | `zizmor --pedantic .github/workflows/` |

Resolve a pin:

```bash
tag=$(gh api repos/<owner>/<repo>/releases/latest --jq .tag_name)
gh api repos/<owner>/<repo>/commits/"$tag" --jq .sha
```

Read [references/hardening-patterns.md](references/hardening-patterns.md) before writing a release workflow: a complete pinned example and the Pwn Request pattern.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Tags like `@v4` are fine for a research lab" | TeamPCP moved exactly such tags. Your token still publishes to PyPI. |
| "The token works, OIDC can wait" | A working long-lived token is what gets stolen. |
| "We'll harden after the deadline" | The release run exposes the secrets. Fixes take minutes. |
| "Pinning is enough" | Every step still gets write-all and the token. |
| "Upstream's README uses `@release/v1`" | Pin the SHA anyway. |

## Red Flags: stop before tagging

- A `uses:` ref that isn't 40 hex characters
- `id-token: write` or a registry secret in a job that installs or tests
- `allow-unsafe-pr-checkout: true`
- "Ship now, harden next week"

## Common Mistakes

- A step left on a branch ref, such as `pypa/gh-action-pypi-publish@release/v1`.
- Snippets that don't parse (`permissions:` then a bare `- uses:`). Validate before proposing.
- `@...` or `<sha>` placeholders without the resolve command.
- `environment:` without required reviewers gates nothing.
- Trusting zizmor's default persona: 1.32.0 flagged `write-all` only with `--pedantic`.

Report findings as file:line, violation, exact fix.
