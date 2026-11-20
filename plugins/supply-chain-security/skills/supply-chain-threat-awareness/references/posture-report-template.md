# Posture Report Template

Use this template when producing the output of a supply-chain threat-posture review. Fill in every cell — `UNKNOWN` is a valid value when evidence is missing and signals a gap to investigate.

```markdown
## Supply Chain Threat Posture: <project>

### Campaign Applicability (campaigns observed 2025–2026)

| Campaign | Applicable | Evidence |
|----------|------------|----------|
| Shai-Hulud | YES/NO/UNKNOWN | <package and lockfile line, or reason "no npm deps"> |
| TeamPCP | YES/NO/UNKNOWN | <action ref and workflow line, or affected package and lockfile line, or reason "no GHA, no affected packages"> |
| axios | YES/NO/UNKNOWN | <package and lockfile line> |
| LiteLLM .pth | YES/NO/UNKNOWN | <litellm version and .pth check result> |

### Audit Results

| Step | PASS | WARN | FAIL | Findings |
|------|------|------|------|----------|
| 1 — Lockfiles | <n> | <n> | <n> | <file:line>: <description> |
| 2 — Action pinning | <n> | <n> | <n> | <file:line>: <description> |
| 3 — Install-time code | <n> | <n> | <n> | <file:line>: <description> |
| 4 — Cooldown | <n> | <n> | <n> | <package version>: <age when adopted> |
| 5 — Provenance | <n> | <n> | <n> | <file:line>: <description> |

### Top 3 Priority Actions

1. <highest-impact remediation> — run `/supply-chain-<command>` or follow `<skill>`
2. <second priority> — <command or skill>
3. <third priority> — <command or skill>
```

## Finding entry rules

For each finding, the entry MUST include:

- Campaign or pattern name (e.g., "TeamPCP — mutable action ref").
- `file:line` citation (the workflow, lockfile, or manifest where the issue lives).
- Blast radius (which secrets/environments would be exposed if exploited).
- Remediation: the concrete fix and the skill that covers it (e.g., "pin to the full commit SHA", `supply-chain-hardened-ci-cd`). Name a `/supply-chain-*` command only if it is in your available commands.
