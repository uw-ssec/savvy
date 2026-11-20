# Releasing

The full release checklist is tracked in [#132](https://github.com/uw-ssec/savvy/issues/132). This page covers the citation steps and the signed skill archives.

## Citation and DOI

Zenodo archives each published GitHub Release and mints a DOI for it. It takes the title, authors, abstract, keywords, and license from [`CITATION.cff`](../CITATION.cff) at the release tag, and the version and date from the release itself.

1. **Before every release:** confirm `uw-ssec/savvy` is switched on at zenodo.org → Account → GitHub. A release published while it is off gets no DOI.
2. **Before tagging:** in `CITATION.cff`, set `version` to the tag without the `v` (tag `v26.11.0` → `version: 26.11.0`) and `date-released` to the release date (`YYYY-MM-DD`). Zenodo ignores these two fields; they are for GitHub's **Cite this repository**. Validate and commit:

   ```bash
   pixi exec cffconvert --validate -i CITATION.cff
   ```

   An invalid `CITATION.cff` makes the Zenodo archive fail, so no DOI is minted.
3. **Publish the GitHub Release.** A draft does not trigger Zenodo, but a pre-release does: it is archived like any other release and gets a permanent DOI. Don't publish test or release-candidate releases on `uw-ssec/savvy`.
4. **After publishing:** within a few minutes the release should appear at zenodo.org → Account → GitHub. Check the record's title and authors. Its version is `v26.11.0`, taken from the tag, not `26.11.0` from `CITATION.cff`; that difference is expected. If the archive failed, the error is shown there.

## Signed skill archives

The skills in the trust-pilot plugin (`ai-research-workflows` for now) ship as signed archives instead of a plugin zip. The [`release` skill](../.agents/skills/release/SKILL.md) builds no zip for them.

[`release-sign.yml`](../.github/workflows/release-sign.yml) runs when a release is **published**, not when it's drafted. For each pilot skill it stages a copy of the skill directory, signs it with [OpenSSF model signing](https://github.com/sigstore/model-transparency) using Sigstore keyless signing (the workflow's own GitHub identity, no stored key), and packs it as `<plugin>--<skill>-<version>.tar.gz`. The version has no `v`. Each archive has the root folder `<plugin>--<skill>/` and contains the signature, `skill.oms.sig`. The job verifies one archive, then uploads all of them to the release.

The first signed release is the first one tagged after the pilot lands. `v26.11.0` ships unsigned.

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
