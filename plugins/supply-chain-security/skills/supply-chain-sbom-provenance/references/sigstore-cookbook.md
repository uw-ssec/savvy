# Sigstore Cookbook

Outputs shown were checked in November 2026 with cosign v3.1.3, gh 2.96.0, syft 1.57.2 and pypi-attestations 0.0.30.

## Contents

- [What Sigstore Provides](#what-sigstore-provides)
- [Sign an Artifact in CI](#sign-an-artifact-in-ci)
- [Verify a Downloaded Artifact](#verify-a-downloaded-artifact)
- [Worked Examples](#worked-examples)
- [SBOMs with syft](#sboms-with-syft)
- [npm Provenance and Trusted Publishing](#npm-provenance-and-trusted-publishing)
- [Transparency Log Lookup](#transparency-log-lookup)
- [Common Failure Modes](#common-failure-modes)

## What Sigstore Provides

Sigstore is keyless signing for software artifacts. The signer authenticates via OIDC (GitHub Actions, Google, Microsoft, etc.); Fulcio issues a short-lived X.509 cert (~10 min validity) bound to that OIDC identity; cosign signs the artifact with that cert; the signature and cert are logged to Rekor, a public append-only transparency log. There are no long-lived signing keys to rotate, leak, or revoke — the identity proof lives in the transparency log entry.

GitHub artifact attestations from public repositories use this public Sigstore instance. Private repositories use GitHub's own Sigstore instance, which has no transparency log, so there is no Rekor entry to check.

## Sign an Artifact in CI

Job-level permissions and the signing step (the complete workflow is `assets/sbom-workflow.yml`):

```yaml
permissions: {}
jobs:
  sign:
    runs-on: ubuntu-latest
    permissions:
      contents: write   # upload to the release
      id-token: write   # lets the job request an OIDC token from GitHub
    steps:
      - uses: sigstore/cosign-installer@756fe2d284c7292c4e9b62c8a28f1e5629c59532  # v4.1.3
      - name: Sign artifact
        run: cosign sign-blob --yes --bundle <artifact>.sigstore.json <artifact>
```

`--yes` skips the interactive prompt, which CI needs. `--bundle` writes one self-contained file (certificate, signature and Rekor entry) that verifiers consume. cosign-installer v4.1.3 installs cosign v3.1.4 unless you set `cosign-release`.

`actions/attest-build-provenance` is the GitHub-native alternative: it stores a SLSA provenance attestation in GitHub's attestation API, where `gh attestation verify` finds it. It writes nothing into `dist/` (its `bundle-path` output names the bundle file it leaves on the runner). From v4 it wraps `actions/attest`, which new workflows can use directly.

## Verify a Downloaded Artifact

**cosign bundle.** Pin the exact identity:

```bash
cosign verify-blob --bundle <file>.sigstore.json \
  --certificate-identity https://github.com/<owner>/<repo>/.github/workflows/<workflow>.yml@refs/tags/<tag> \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  <file>
```

To accept any release tag, use a regexp anchored at both ends with escaped dots. cosign does not anchor it for you: an unanchored pattern matches anywhere in the certificate's SAN.

```bash
--certificate-identity-regexp '^https://github\.com/<owner>/<repo>/\.github/workflows/<workflow>\.yml@refs/tags/v[0-9.]+$'
```

The GitHub Actions OIDC issuer is always `https://token.actions.githubusercontent.com`.

**GitHub attestation.** `--repo` alone accepts any workflow in that repository, and `--owner` accepts any repository of that owner, so add `--signer-workflow`:

```bash
gh attestation verify <file> --repo <owner>/<repo> \
  --signer-workflow <owner>/<repo>/.github/workflows/<workflow>.yml \
  --source-ref refs/tags/<tag>
```

If a reusable workflow made the attestation, that reusable workflow is the signer: pass its path to `--signer-workflow`. On success the command exits 0 and prints nothing when its output isn't a terminal; add `--format json` to see the certificate fields.

**PyPI.** Trusted publishing through `pypa/gh-action-pypi-publish` uploads PEP 740 attestations by default:

```bash
pypi-attestations verify pypi --repository https://github.com/<owner>/<repo> pypi:<file>
```

**npm.** `npm audit signatures` checks registry signatures and provenance attestations for installed packages.

## Worked Examples

GitHub attestation, PyPI attestation and exact cosign identity, all passing:

```bash
gh release download v4.5.1 --repo sigstore/sigstore-python --pattern 'sigstore-4.5.1.tar.gz'
gh attestation verify sigstore-4.5.1.tar.gz --repo sigstore/sigstore-python \
  --signer-workflow sigstore/sigstore-python/.github/workflows/release.yml \
  --source-ref refs/tags/v4.5.1                    # exit 0
pypi-attestations verify pypi --repository https://github.com/sigstore/sigstore-python \
  pypi:sigstore-4.5.1.tar.gz                       # OK: sigstore-4.5.1.tar.gz

# cosign's own releases are signed from Google Cloud, not GitHub Actions:
gh release download v3.1.4 --repo sigstore/cosign \
  --pattern 'cosign-darwin-arm64' --pattern 'cosign-darwin-arm64.sigstore.json'
cosign verify-blob --bundle cosign-darwin-arm64.sigstore.json \
  --certificate-identity keyless@projectsigstore.iam.gserviceaccount.com \
  --certificate-oidc-issuer https://accounts.google.com \
  cosign-darwin-arm64                              # Verified OK
```

## SBOMs with syft

What syft 1.57.2 catalogs from a Python project:

| Scan target | Components found |
|---|---|
| `syft <name>.whl` | none |
| `syft <name>.tar.gz` (hatchling sdist) | none |
| `syft <name>.tar.gz` (setuptools sdist with `.egg-info`) | the package itself, plus pins from any `requirements-dev.txt`; no runtime dependencies |
| `syft dir:dist/` | none |
| `syft dir:.` with only `pyproject.toml` ranges | none |
| `syft dir:.` with a pinned `requirements.txt` | the pinned lines |
| `syft dir:<venv>` after installing the wheel | the package and every installed runtime dependency, with versions |

Scan the installed environment (see `SKILL.md`). For a single-file source, syft writes the file's digest to `metadata.component.version` as `sha256:<hex>`; `metadata.component.hashes` stays empty. Check digests against `SHA256SUMS` or the attestation subject instead.

Container image (SPDX shown; CycloneDX works the same way):

```bash
syft <registry>/<image>:<tag> -o spdx-json=sbom.spdx.json
```

To attest an SBOM rather than attach it, `actions/attest` accepts an SPDX or CycloneDX file through `sbom-path`.

## npm Provenance and Trusted Publishing

Provenance comes from the CI job's OIDC token, not from a setting on the npm account.

- **Trusted publishing (preferred):** in the package's settings on npmjs.com, add a Trusted Publisher with the GitHub owner, repository, workflow file name and, optionally, environment. Requires npm CLI 11.5.1+ and Node 22.14.0+, `id-token: write` on the publish job, and a GitHub-hosted runner. No token is stored, and provenance is generated automatically without `--provenance`.
- **Token publishing:** `npm publish --provenance --access public` (npm 9.5.0+) on a GitHub-hosted runner with `id-token: write`. The `repository` field in `package.json` must match the publishing repository.
- npm generates no provenance for packages published from private repositories.

## Transparency Log Lookup

```bash
# Rekor log index and time (Unix seconds) from a blob bundle
jq '.verificationMaterial.tlogEntries[] | {logIndex, integratedTime}' <file>.sigstore.json

# The same entry from Rekor
curl -s "https://rekor.sigstore.dev/api/v1/log/entries?logIndex=<logIndex>"

# Verified timestamps of a GitHub attestation
gh attestation verify <file> --repo <owner>/<repo> --format json \
  --jq '.[].verificationResult.verifiedTimestamps'

# Every Rekor entry for an artifact digest
rekor-cli search --sha <sha256-of-artifact>

# Signatures, attestations and SBOMs attached to an OCI image (images only, not blobs)
cosign tree <registry>/<image>:<tag>
```

If a maintainer's identity was compromised, the malicious signature still shows up in Rekor — bound to the attacker's OIDC identity, signed at a timestamp out of band with normal releases. The log itself is the audit trail.

## Common Failure Modes

- **Missing `id-token: write` permission** — `cosign sign-blob` can't get an OIDC token. Add it to the job's `permissions:` block.
- **Clock skew on the runner** — Fulcio rejects certs whose `notBefore` is in the future. Self-hosted runners with bad NTP fail intermittently. Fix: run `timedatectl status` or `chronyc tracking` on the runner.
- **Identity mismatch** — `cosign verify-blob` fails with `expected SAN value "<expected>", got "<actual>"`. The `<actual>` value is the workflow that really signed the file: compare it with the one you expected.
- **Unanchored identity regexp** — passes for identities you didn't intend. Anchor with `^…$` and escape dots.
- **Expired short-lived cert** — Fulcio certs expire ~10 minutes after issue. The bundle's Rekor entry proves the signature was made while the cert was valid, so verification still works years later. For air-gapped verification, also pass a saved trusted root with `--trusted-root`.
- **No bundle on the release** — `actions/attest-build-provenance` puts no `.sigstore.json` file in `dist/`; consumers use `gh attestation verify` instead. Upload a bundle only when a `cosign sign-blob --bundle` step made one.
