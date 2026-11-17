---
name: supply-chain-sbom-provenance
description: Use when a request involves an SBOM or software bill of materials (CycloneDX, SPDX, syft), Sigstore or cosign keyless signing, signing release artifacts, build provenance or attestations, `gh attestation verify`, npm provenance, a release pipeline's SLSA level, or verifying a downloaded release.
metadata:
  references: references/sigstore-cookbook.md references/slsa-levels.md references/provenance-report-template.md
  assets: assets/sbom-workflow.yml
---

# Supply Chain SBOM and Provenance

Generate SBOMs, sign and attest release artifacts, and verify a downloaded release against the exact workflow that built it.

## Overview

An SBOM lists what a release contains; provenance is a signed record of which repository, workflow and ref built each file. A passing check proves the file came from that workflow at that ref, unchanged. It catches uploads from outside the pipeline (a stolen registry token, a swapped release asset). It does **not** prove the build was clean: a hijacked action inside the legitimate release job (the TeamPCP pattern) gets valid provenance. Pair it with SHA-pinned actions from the `supply-chain-hardened-ci-cd` skill.

## When to Use

- Adding an SBOM, signatures or attestations to a release.
- Verifying a downloaded artifact before installing it.
- Rating a pipeline's SLSA build level or writing a provenance posture report.

For action pinning and workflow permissions, use `supply-chain-hardened-ci-cd`.

## Quick Reference

| Registry | Produce | Verify |
|---|---|---|
| PyPI | Trusted publishing via `pypa/gh-action-pypi-publish` (attests by default) | `pypi-attestations verify pypi --repository https://github.com/<owner>/<repo> pypi:<file>` |
| npm | Trusted publishing (provenance automatic) or `npm publish --provenance` | `npm audit signatures` |
| GitHub release assets | `actions/attest-build-provenance`, `cosign sign-blob --bundle` | below |
| GHCR | `actions/attest-build-provenance` with `push-to-registry: true` | `gh attestation verify oci://<image> --repo <owner>/<repo>` |
| No OIDC | cosign with a KMS or hardware key | `cosign verify-blob --key <key-ref>` |

GitHub attestations alone reach SLSA Build L2 (`references/slsa-levels.md`).

## Produce

`assets/sbom-workflow.yml` is a complete release workflow (build, SBOM, attest, sign, upload) and sets the file names: `sbom.cdx.json`, `SHA256SUMS`, `<file>.sigstore.json`.

For Python, scan an installed environment. syft lists no runtime dependencies from a wheel, an sdist or `dist/`:

```bash
python -m venv --without-pip sbom-env
python -m pip --python sbom-env/bin/python install dist/*.whl
syft dir:sbom-env --source-name <project> --source-version <version> -o cyclonedx-json=sbom.cdx.json
```

## Verify a Downloaded Release

Pin one repository, workflow file and tag:

```bash
cosign verify-blob --bundle <file>.sigstore.json \
  --certificate-identity https://github.com/<owner>/<repo>/.github/workflows/<workflow>.yml@refs/tags/<tag> \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  <file>

# When the release has GitHub attestations:
gh attestation verify <file> --repo <owner>/<repo> \
  --signer-workflow <owner>/<repo>/.github/workflows/<workflow>.yml \
  --source-ref refs/tags/<tag>
```

Then run `sha256sum -c --ignore-missing SHA256SUMS`, and confirm the Rekor time (`jq '.verificationMaterial.tlogEntries[].integratedTime' <file>.sigstore.json`, Unix seconds) falls in the release window. Any failure means unverified: don't install.

Failure modes and recipes: `references/sigstore-cookbook.md`. Pipeline reviews: fill in `references/provenance-report-template.md`.

## Common Mistakes

| Mistake | Fix |
|---|---|
| `--certificate-identity-regexp ".../.github/workflows/.+"` (any workflow) | Exact `--certificate-identity`, or `--signer-workflow` |
| `cosign tree <file>` for the Rekor time | `cosign tree` reads OCI images; use the bundle's `integratedTime` |
| `gh attestation list` | Doesn't exist; use `gh attestation verify` |
| Uploading `dist/*.sigstore` after `attest-build-provenance` | It writes nothing to `dist/`; bundle files come from `cosign sign-blob --bundle` |
| Digest in `metadata.component.hashes` | syft doesn't write it; use `SHA256SUMS` or the attestation subject |
| "Verified, so the build was clean" | It proves which workflow built the file, nothing more |
