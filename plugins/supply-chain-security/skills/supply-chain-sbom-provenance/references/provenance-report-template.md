# Provenance Posture Report Template

Use this template when reviewing a project's release pipeline for SBOM, signing and provenance. Every PASS/WARN/FAIL cites a `file:line` from the workflows, or says "absent" when the control is missing.

```markdown
## Provenance Posture: <project>

### Generation Posture
| Criterion | PASS/WARN/FAIL | Evidence |
|-----------|----------------|----------|
| SBOM generated for releases | ... | <workflow file:line or "absent"> |
| SBOM scans an installed environment or lockfile, not `dist/` | ... | <scan target> |
| SBOM format (CycloneDX/SPDX) | ... | <format detected> |
| Build provenance attestation | ... | <workflow file:line> |
| Sigstore signing (`cosign sign-blob --bundle`) | ... | <workflow file:line or N/A> |
| PyPI/npm trusted publishing with attestations or provenance | ... | <evidence or N/A> |
| Actions in the release job pinned by SHA | ... | <evidence; see the supply-chain-hardened-ci-cd skill> |
| SLSA build level achieved | ... | <level + reasoning, see references/slsa-levels.md> |

### Verification Posture
| Criterion | PASS/WARN/FAIL | Evidence |
|-----------|----------------|----------|
| Downstream verification documented | ... | <README/docs reference> |
| Documented command pins repo, workflow file and ref | ... | <command quoted; FAIL on `.github/workflows/.+` or `.*`> |
| Bundles, SBOM and `SHA256SUMS` attached to the release | ... | <release page or workflow file:line> |

### Top 3 Priority Actions
1. <highest-impact upgrade> — apply `assets/sbom-workflow.yml` or follow `references/sigstore-cookbook.md`
2. <second priority>
3. <third priority>
```
