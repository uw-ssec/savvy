# Releasing

The full release checklist is tracked in [#132](https://github.com/uw-ssec/savvy/issues/132). This page covers the citation steps.

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
