# Releasing

The full release checklist is tracked in [#132](https://github.com/uw-ssec/savvy/issues/132). This page covers the citation steps and the signed skill archives.

## Citation and DOI

[`zenodo-publish.yml`](../.github/workflows/zenodo-publish.yml) archives savvy on Zenodo through the API, using the [`zenodo-publish`](../.github/actions/zenodo-publish/action.yml) action. It uploads a zip of the source at the commit and takes the title, authors, abstract, keywords, and license from [`CITATION.cff`](../CITATION.cff). Records belong to SSEC's shared Zenodo account, through the org secrets `ZENODO_TOKEN` and `ZENODO_SANDBOX_TOKEN`.

| Event | Zenodo | Version |
|---|---|---|
| GitHub Release published | zenodo.org: a new version of the savvy record, with a permanent DOI | The tag without the `v`, e.g. `26.11.0` |
| Push to `main` | sandbox.zenodo.org: a rehearsal of the same steps; sandbox DOIs are never registered | `CITATION.cff`'s version plus `g` and the commit, e.g. `26.11.0+g1ad2911` |

The workflow finds the savvy record by its keyword `uw-ssec-software:savvy`. The first run on each host creates the record, and every later run adds a version to it, so the concept DOI stays the same.

1. **Keep the Zenodo GitHub integration off** for `uw-ssec/savvy` (zenodo.org → Account → GitHub). With both on, every release gets two records.
2. **Before tagging:** in `CITATION.cff`, set `version` to the tag without the `v` (tag `v26.11.0` → `version: 26.11.0`) and `date-released` to the release date (`YYYY-MM-DD`). The workflow fails before uploading anything if the tag and `version` differ. Validate and commit:

   ```bash
   pixi exec cffconvert --validate -i CITATION.cff
   ```

   Check that the latest `Zenodo publish` run on `main` succeeded: it publishes the same metadata to the sandbox.
3. **Publish the GitHub Release.** A draft does not trigger the workflow, and the workflow skips a pre-release. Don't publish test or release-candidate releases on `uw-ssec/savvy` anyway.
4. **After publishing:** the `Zenodo publish` run's summary links the record and gives its DOI and concept DOI. Check the record's title and authors on zenodo.org.

## Signed skill archives

The skills in the trust-pilot plugin (`ai-research-workflows` for now) ship as signed archives instead of a plugin zip. The [`release` skill](../.agents/skills/release/SKILL.md) builds no zip for them.

[`release-sign.yml`](../.github/workflows/release-sign.yml) runs when a release is **published**, not when it's drafted. For each pilot skill it stages a copy of the skill directory, signs it with [OpenSSF model signing](https://github.com/sigstore/model-transparency) using Sigstore keyless signing (the workflow's own GitHub identity, no stored key), and packs it as `<plugin>--<skill>-<version>.tar.gz`. The version has no `v`. Each archive has the root folder `<plugin>--<skill>/` and contains the signature, `skill.oms.sig`. The job unpacks every archive and verifies its signature against the workflow's identity, then uploads all of them to the release. A failed verification stops the job before any upload.

Signing starts with the first release cut after the pilot merges. Releases cut before that carry no signed archives.

**To confirm after publishing:**

```bash
gh run list --workflow release-sign.yml --limit 3
gh release view <TAG> --json assets --jq '.assets[].name'
```

The run must have succeeded, and the release must list one archive per pilot skill. If the run failed, fix the cause and re-run it with `gh run rerun <run-id>`; the upload replaces any existing assets. Users verify an archive as described in [Checking a skill before you install it](trust-and-safety.md#checking-a-skill-before-you-install-it).

**Recommended repository settings (maintainers).** A signature proves which workflow and tag produced an archive, so protect what feeds it. These are settings in GitHub, not something this repository enforces:

- A tag ruleset for `v*` that restricts who can create, update and delete release tags.
- Optionally, a GitHub environment with required reviewers for the signing job, so a person approves each signing run.
- Branch protection on `main` with **Require review from Code Owners**, so the code at a tag was reviewed.
