---
name: supply-chain-incident-response
description: "Use when responding to a supply-chain incident: an advisory, CVE or GHSA names a dependency or GitHub Action this project uses; a package version was compromised or malicious; a compromised GitHub Action, tag hijack or maintainer account takeover; or CI ran a bad version during an exposure window. Also use when asked for the incident-response runbook, to rotate secrets, or for an incident report."
metadata:
  references: references/runbook-account-takeover.md references/runbook-tag-hijack.md references/secret-rotation.md
  assets: assets/incident-report-template.md
---

# Supply Chain Incident Response

**An incident stays open until all four checks (lockfile, CI cache, secrets, persistence) have PASS, EXPOSED or UNKNOWN and evidence in the incident report.**

## When to Use

An advisory, CVE, GHSA or campaign names a dependency or Action you use. Before an incident, use `supply-chain-threat-awareness`.

## Quick Reference: 4-Point Check

Set the **exposure window** first: when the bad version was installable, in UTC. Get the affected range (GHSA: `-f ghsa_id=<GHSA-ID>`):

```bash
gh api -X GET /advisories -f cve_id=<CVE-ID> --jq '.[] | {ghsa_id, affected: [.vulnerabilities[] | {pkg: .package.name, range: .vulnerable_version_range}]}'
```

`<lockfiles>` means `'*package-lock.json' '*yarn.lock' '*pnpm-lock.yaml' '*uv.lock' '*poetry.lock' '*pixi.lock' '*conda-lock.yml' '*Cargo.lock' '*go.sum'` (`*` also matches nested lockfiles).

| Check | Command | Evidence |
|---|---|---|
| 1 Lockfile | `git grep -nwF -A3 '<pkg>' -- <lockfiles>`, then `git log -G'<bad-version>' --format='%h %cI %s' -- <lockfiles>` | `file:line`; when the bad version entered |
| 2 CI cache | `gh cache list --sort created_at --order desc --limit 1000 --json id,key,createdAt` | ids with `createdAt` at or after the window start |
| 3 Secrets | `gh secret list`, `gh secret list --env <env>`, `grep -rnw 'secrets' .github/workflows/` | every secret the affected jobs could read (`secrets: inherit` passes all) |
| 4 Persistence | the runbook below | artifacts found, or "none" with the commands run |

## Response Order

1. **Contain:** pin a known-good version in every lockfile; delete each cache from check 2 (loop in `references/runbook-account-takeover.md`); disable workflows that ran the bad version (`gh workflow disable <workflow>`).
2. **Eradicate:** rotate every secret from check 3. Hunt persistence.
3. **Recover:** with caches gone, `gh workflow enable <workflow>`, then run it from the fixed commit (push, tag, or `gh workflow run <workflow> --ref <branch>` if it has `workflow_dispatch`); a re-run reuses the old commit. Verify any attestations with `supply-chain-sbom-provenance`.
4. **Report:** fill every section of `assets/incident-report-template.md`. If this project shipped an affected version, file a GHSA.

## Runbooks

- Maintainer account takeover (npm, PyPI): `references/runbook-account-takeover.md`
- Compromised Action or tag hijack (check 1 is the `uses:` refs): `references/runbook-tag-hijack.md`
- Secret rotation: `references/secret-rotation.md`
- `.pth` files: the PyPI `.pth` check in `supply-chain-ecosystem-quirks`.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The scanner is clean and the lockfile is fixed" | Both describe today, not the window. |
| "Only the npm token touched npm" | Install scripts read the whole environment: every secret the job could read is exposed. |
| "Caches expire anyway" | Only after 7 days unused; each restore resets the clock. Restore-keys copy old contents into new caches. |

**Red flags:** a check left blank; one secret rotated out of several; checks skipped for a release deadline.

## Common Mistakes

- `gh actions cache …` doesn't exist; use `gh cache list` and `gh cache delete <id>`.
- `'**/lock*'` matches no standard lockfile; use `<lockfiles>`.
- `git log -S` misses a bump when another package leaves that version. Use `-G'1\.2\.4'`.
- `find -newer <date>` expects a file. Use `-newermt "<YYYY-MM-DD HH:MM> UTC"`.
