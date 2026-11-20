---
name: release
description:
  Use when a new version needs cutting — a calendar version, changelog entry,
  git tag, GitHub release, and plugin zip assets.
---

# Release

Create a versioned release with changelog, tag, GitHub release, and plugin zip
assets.

## Arguments

None. The version is the current date (see `docs/versioning.md`).

## Instructions

1. Get the previous release tag:

   - Check `git tag --sort=-v:refname | head -1` for the latest tag
   - If no tags exist, there is no previous release

2. Calculate the new version using calendar versioning, `YY.M.MICRO`, per
   `docs/versioning.md`:

   - `YY.M` is today's two-digit year and month, with no zero-padding
     (`v26.4.0`, never `v26.04.0`)
   - MICRO counts releases already tagged in that month, starting at 0

3. Compute the set of changed plugins **before editing any manifest**:

   ```bash
   pixi run -e ci python .github/scripts/skill_trust.py changed-plugins <previous-tag>
   ```

   Set each listed plugin's `version` in its `plugin.json` to the new version
   (without the `v`), run `pixi run plugins-sync`, and commit the bumps before
   tagging. Plugins not listed keep their version.

4. Verify readiness:

   - `git status` — must be on `main` with no uncommitted changes
   - `git pull origin main` — must be up to date
   - Warn and stop if not on `main` or if there are uncommitted changes

5. Read `CHANGELOG.md` and check that the `[Unreleased]` section has content.

6. Update `CHANGELOG.md`:

   - Rename `[Unreleased]` to `[YY.M.MICRO] -- YYYY-MM-DD` (today's date)
   - Add a new empty `[Unreleased]` section above it

7. Commit the changelog update:

   ```bash
   git add CHANGELOG.md
   git commit -m "chore(release): prepare vYY.M.MICRO" -m "Assisted-by: <harness>:<model>"
   ```

   The trailer follows the `commit` skill's AI Attribution section. Omit it
   entirely if the release was cut without AI assistance.

8. Create the git tag:

   ```bash
   git tag -a vYY.M.MICRO -m "vYY.M.MICRO"
   ```

9. Push the commit and tag:

   ```bash
   git push origin main --follow-tags
   ```

10. Build plugin zip assets:

    - For each directory in `plugins/`, create a zip archive
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

11. Create a GitHub release with plugin zips as assets:

    ```bash
    gh release create vYY.M.MICRO --title "vYY.M.MICRO" \
      --notes "$(cat <<'EOF'
    ## What's Changed

    <extract the relevant section from CHANGELOG.md>

    ## Plugin Assets

    <list each plugin zip with name and description>

    **Full Changelog**: <repo compare URL>/compare/vPREVIOUS...vYY.M.MICRO
    EOF
    )" \
      plugin_name_MM_DD_YYYY.zip
    ```

12. Clean up zip files from the repo root after successful upload.

13. Confirm: "Released vYY.M.MICRO — <release URL>"

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
- Never commit generated zip files — they are upload artifacts only
- NEVER add "Generated with" or similar marketing lines to the release notes
- NEVER include sensitive information in the release notes or changelog
