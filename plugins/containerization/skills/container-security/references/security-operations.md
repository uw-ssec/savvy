# Security Operations -- Validation Gates and Recovery

## Validation Gates (CI/CD)

Apply explicit gates in order:

1. **Scan Gate** -- fail build on policy threshold:

```bash
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:latest
```

2. **Post-fix Re-scan Gate** -- confirm findings are reduced/cleared after remediation.
3. **SBOM Gate** -- ensure SBOM file is generated and archived.
4. **Signature Gate** -- require successful `cosign sign` and `cosign verify` before publish.

## Suppression Policy

Suppress only with rationale and tracking issue.

### Trivy

`.trivyignore`:

```text
# Not reachable in runtime path; tracked in SEC-123
CVE-2024-1234
```

### Grype

`.grype.yaml`:

```yaml
ignore:
  - vulnerability: CVE-2024-1234
    reason: "Not reachable in production path; tracked in SEC-123"
```

## Failure Recovery Playbook

1. **Unexpected scan spike:** check DB update freshness and image tag drift.
2. **Unfixed critical CVE:** switch base image or remove vulnerable package path.
3. **False positive suspicion:** confirm package actually present, then suppress with issue link.
4. **cosign failure:** verify identity/token, transparency log reachability, and image reference.
5. **CI timeout on scans:** narrow scope or cache scanner database.

## Minimal CI Sequence

```yaml
# Assumes an earlier build-and-push step with `id: build` (its `digest` output
# names the pushed image) and `permissions: id-token: write` for keyless signing.
# Scan, SBOM and sign the same immutable digest.
- name: Scan image
  run: trivy image --severity HIGH,CRITICAL --exit-code 1 myregistry/myapp@${{ steps.build.outputs.digest }}

- name: Generate SBOM
  run: syft myregistry/myapp@${{ steps.build.outputs.digest }} -o spdx-json > sbom.spdx.json

- name: Sign image
  run: cosign sign --yes myregistry/myapp@${{ steps.build.outputs.digest }}

# Keyless verify must name the signer; here, this workflow run
- name: Verify signature
  run: |
    cosign verify \
      --certificate-identity "https://github.com/${{ github.workflow_ref }}" \
      --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
      myregistry/myapp@${{ steps.build.outputs.digest }}
```
