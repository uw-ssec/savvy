---
name: release
description:
  Use when a new version needs cutting — a calendar version, changelog entry,
  git tag, GitHub release, plugin zip assets, and signed pilot skill archives.
---

# Release

Create a versioned release with changelog, tag, GitHub release, and plugin zip
assets. Pilot plugins (`ai-research-workflows`) get no zip: `release-sign.yml`
attaches signed per-skill archives when the release is published (see
`docs/releasing.md`).

## Arguments

None. The version is the current date (see `docs/versioning.md`).

## Instructions

1. Get the previous release tag:

   - Check `git tag --sort=-v:refname | head -1` for the latest tag
   - If no tags exist, there is no previous release (see step 4)

2. Calculate the new version using calendar versioning, `YY.M.MICRO`, per
   `docs/versioning.md`:

   - `YY.M` is today's two-digit year and month, with no zero-padding
     (`v26.4.0`, never `v26.04.0`)
   - MICRO counts releases already tagged in that month, starting at 0

3. Verify readiness:

   - `git status` — must be on `main` with no uncommitted changes
   - `git pull origin main` — must be up to date
   - Warn and stop if not on `main` or if there are uncommitted changes

4. Compute the set of changed plugins. This only reads; edit nothing yet:

   ```bash
   pixi run -e ci python .github/scripts/skill_trust.py changed-plugins <previous-tag>
   ```

   If no previous tag exists (the first release), skip the command: every
   plugin takes the new version. Keep the list for steps 5 and 6.

5. Benchmark the changed pilot skills. Benchmarks report; they never gate the
   release. If `changed-plugins` (step 4) lists `ai-research-workflows`, or this
   is the first release, dispatch the benchmark workflow for the changed
   skills:

   ```bash
   gh workflow run benchmark-skills.yml -f skills=plugins/ai-research-workflows/skills/<skill>,...
   ```

   `skills` takes full skill directories, comma-separated; an empty value runs
   all pilot skills. See the workflow for `model` and `attempts`. The run
   pushes each skill's `BENCHMARK.md` to a `benchmarks/<run_id>-<run_attempt>`
   branch. Open a pull request from it, review it, and merge it before
   tagging, then `git pull origin main` so the version bumps, commits and tag
   below start from the merged result. Publish a FAIL or INCONCLUSIVE result as it is; a maintainer note
   on why is optional.

6. Bump versions. Set each plugin listed in step 4's `changed-plugins` output
   (every plugin, on the first release) to the new version: edit its
   `version` in `plugin.json` (without the `v`), run `pixi run plugins-sync`, and
   commit the bumps before tagging. Plugins not listed keep their version.

7. Read `CHANGELOG.md` and check that the `[Unreleased]` section has content.

8. Update `CHANGELOG.md`:

   - Rename `[Unreleased]` to `[YY.M.MICRO] -- YYYY-MM-DD` (today's date)
   - Add a new empty `[Unreleased]` section above it

9. Commit the changelog update:

   ```bash
   git add CHANGELOG.md
   git commit -m "chore(release): prepare vYY.M.MICRO" -m "Assisted-by: <harness>:<model>"
   ```

   The trailer follows the `commit` skill's AI Attribution section. Omit it
   entirely if the release was cut without AI assistance.

10. Create the git tag:

   ```bash
   git tag -a vYY.M.MICRO -m "vYY.M.MICRO"
   ```

11. Push the commit and tag:

   ```bash
   git push origin main --follow-tags
   ```

12. Build plugin zip assets:

    - For each plugin listed in `.claude-plugin/marketplace.json` except
      `ai-research-workflows`, create a zip archive. Plugins marked
      `released: false` in `docs/catalog.yml` are not listed there and must not
      be zipped. `ai-research-workflows` is a trust-pilot plugin: its signed
      per-skill archives come from `release-sign.yml`, and an unsigned zip
      beside them would be an unverifiable copy.
    - **Zip naming convention:**
      - Default: `plugin_name_MM_DD_YYYY.zip` (snake_case plugin name + date)
      - If a release already exists for today (check `gh release list`), append
        a sequence suffix: `plugin_name_MM_DD_YYYY_2.zip`, `_3.zip`, etc.
    - Example: `recipe_workshop_03_30_2026.zip`, or
      `recipe_workshop_03_30_2026_2.zip` for a second release that day
    - Create zips from within the `plugins/` directory so the zip root is the
      plugin folder itself:
      ```bash
      cd plugins && zip -r ../plugin_name_MM_DD_YYYY.zip plugin-dir-name/ -x "*.DS_Store" "*__pycache__/*" "*.pyc" && cd ..
      ```
    - Exclude unnecessary files from zip: `.DS_Store`, `__pycache__`, `*.pyc`

13. Create a GitHub release with plugin zips as assets:

    ```bash
    gh release create vYY.M.MICRO --title "vYY.M.MICRO" \
      --notes "$(cat <<'EOF'
    ## What's Changed

    <extract the relevant section from CHANGELOG.md>

    ## Plugin Assets

    <list each plugin zip with name and description>

    ## Skill Benchmarks

    <one line per pilot skill: its verdict from `<skill>/BENCHMARK.md`, or "no
    benchmark yet" if the file is missing. Report FAIL and INCONCLUSIVE as
    they are.>

    ## Signed Skill Archives

    Attached by `release-sign.yml` after publishing. To verify one, see
    [Checking a skill before you install it](<repo URL>/blob/vYY.M.MICRO/docs/trust-and-safety.md#checking-a-skill-before-you-install-it).

    **Full Changelog**: <repo compare URL>/compare/vPREVIOUS...vYY.M.MICRO
    EOF
    )" \
      plugin_name_MM_DD_YYYY.zip
    ```

14. Clean up zip files from the repo root after successful upload.

15. Confirm signing. Publishing triggers `release-sign.yml`:

    ```bash
    gh run list --workflow release-sign.yml --limit 3
    gh release view vYY.M.MICRO --json assets --jq '.assets[].name'
    ```

    The run must have succeeded and the release must list one
    `ai-research-workflows--<skill>-YY.M.MICRO.tar.gz` per pilot skill. If it
    failed, read the run log, fix the cause, and re-run it with
    `gh run rerun <run-id>`; re-running replaces the assets.

16. Confirm: "Released vYY.M.MICRO — <release URL>"

## Zip Naming Rules

- Plugin directory name is converted to snake_case: `recipe-workshop` →
  `recipe_workshop`
- Date format is `MM_DD_YYYY`
- Sequence suffix only added when multiple releases occur on the same day
- Sequence starts at `_2` (first release of the day has no suffix)

## Rules

- Must be on `main` branch with no uncommitted changes
- Must have content in `[Unreleased]` section of CHANGELOG.md
- Never create a release from a feature branch
- Tag format is always `vYY.M.MICRO` (with `v` prefix), e.g. `v26.11.0`
- Ask for confirmation before pushing the tag and creating the release
- If CHANGELOG.md doesn't exist or has no `[Unreleased]` section, warn and ask
  how to proceed
- Benchmarks never gate a release, but a pilot skill's verdict (or "no
  benchmark yet") must appear in the release notes
- Never build an unsigned archive for a pilot skill
- Never commit generated zip files — they are upload artifacts only
- NEVER add "Generated with" or similar marketing lines to the release notes
- NEVER include sensitive information in the release notes or changelog
