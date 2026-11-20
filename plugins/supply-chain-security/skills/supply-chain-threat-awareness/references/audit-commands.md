# Audit Commands

Commands for the five audit steps in `SKILL.md`. Run them from the repository root. They were tested on 2026-11-17; the greps behave the same under macOS BSD grep 2.6.0 and GNU grep 3.12.

## Contents

- [Step 1 — Lockfiles](#step-1--lockfiles)
- [Step 2 — Action pinning](#step-2--action-pinning)
- [Step 3 — Install-time code](#step-3--install-time-code)
- [Step 4 — Cooldown](#step-4--cooldown)
- [Step 5 — Provenance](#step-5--provenance)

## Step 1 — Lockfiles

```bash
# Committed lockfiles
git ls-files | grep -E '(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|pixi\.lock|conda-lock\.yml|Cargo\.lock|go\.sum)$'

# Every dependency install in CI; judge each line against the table below
grep -rnE --include='*.yml' --include='*.yaml' '(npm (ci|install|i)|pnpm (install|i)|yarn( install)?|pip3? install|uv (sync|pip install)|poetry install|pixi install|cargo (build|install))([[:space:]]|$)' .github/
```

| Tool | PASS | FAIL |
|---|---|---|
| npm | `npm ci` | `npm install`, `npm i` for project dependencies |
| pnpm | `pnpm install --frozen-lockfile` (the default in CI when a lockfile exists) | `--no-frozen-lockfile` |
| Yarn 1 | `yarn install --frozen-lockfile` | bare `yarn install` |
| Yarn 2+ | `yarn install --immutable` (the default in CI) | `--no-immutable` |
| uv | `uv sync --locked` | `uv sync`; `uv sync --frozen` installs without checking that `uv.lock` matches `pyproject.toml` |
| pixi | `pixi install --locked` | `pixi install`, which updates a stale `pixi.lock` |
| Poetry | `poetry install` with a committed `poetry.lock` (it refuses a stale lock) | no `poetry.lock` |
| pip | `pip install --require-hashes -r <requirements-file>` | `pip install` without hashes |
| Cargo | `cargo build --locked` | `cargo build` |

Checked with `--help` for npm 11.20.0, pnpm 12.21.0, Yarn 1.22.22 and 4.18.1, uv 0.13.9, pixi 0.83.0 and pip 25.0.1; Poetry 2.5.1 against a stale lock; the Cargo docs.

## Step 2 — Action pinning

```bash
git grep --untracked -nE "(^[[:space:]]*(-[[:space:]]+)?|[{,][[:space:]]*)[\"']?uses[\"']?[[:space:]]*:" -- '.github/*.yml' '.github/*.yaml' 'action.yml' '*/action.yml' 'action.yaml' '*/action.yaml' \
  | grep -vE "uses[\"']?[[:space:]]*:[[:space:]]*[^[:alnum:][:space:]]?\./" \
  | grep -vE "uses[\"']?[[:space:]]*:[[:space:]]*[\"']?[^[:space:]\"',}]+@[0-9a-f]{40}[\"']?([[:space:]},]|$)" \
  | grep -vE 'docker://[^[:space:]]*@sha256:[0-9a-f]{64}' \
  || echo "OK: every uses: ref is SHA- or digest-pinned, or local"
```

Every line it prints is a FAIL. The scan reads the `.yml` and `.yaml` files under `.github/` and every `action.yml` or `action.yaml` in the repository, tracked or not (files matched by `.gitignore` are skipped), so local composite actions are checked wherever they live (`./actions/build` as well as `./.github/actions/lint`). It accepts only:

- a full 40-character commit SHA that ends the ref, optionally quoted and followed by a comment (`@<sha>/maintenance` is a branch, not a pin);
- a local `./` path;
- a `docker://` image pinned by `@sha256:` digest.

Everything else is flagged: tags (`@v4`, `@0.34.2`), branches (`@main`, `@dev`, `@beta`), short SHAs, `docker://` tags, and reusable workflows called on a branch.

It finds `uses:` in block style, in flow mappings (`- {uses: …}`) and under a quoted key (`"uses": …`). It reads one line at a time, so a line holding several refs (`steps: [{uses: …}, {uses: …}]`) passes if any one of them is pinned: check such lines by hand.

A pinned composite action can still call actions by tag. To check one, list the `uses:` lines of its `action.yml` (or `action.yaml`) at the pinned SHA:

```bash
gh api 'repos/<owner>/<repo>/contents/action.yml?ref=<sha>' --jq .content | base64 --decode | grep -n 'uses:'
```

Fix: pin each ref to its full commit SHA (with `/supply-chain-pin-actions`, dry run first, if that command is available), then rerun the scan.

## Step 3 — Install-time code

```bash
# The project's own lifecycle scripts
jq '.scripts // {} | with_entries(select(.key | test("^((pre|post)?(install|prepare)|prepublish|dependencies)$")))' package.json

# Dependencies with install scripts (package-lock.json v2 and v3 record hasInstallScript)
jq -r '.packages | to_entries[] | select(.key != "" and .value.hasInstallScript) | .key' package-lock.json

# Every npm install in CI
grep -rnE --include='*.yml' --include='*.yaml' '(^|[^[:alnum:]])npm (ci|install|i)([[:space:]]|$)' .github/
# Anything in CI that turns scripts back on (--no-ignore-scripts, --ignore-scripts=false, npm_config_ignore_scripts)
grep -rniE --include='*.yml' --include='*.yaml' "no-ignore-scripts|ignore[-_]scripts([[:space:]]*[=:][[:space:]]*|[[:space:]]+)[\"']?false" .github/
# The repo-wide setting
grep -nE '^ignore-scripts[[:space:]]*=' .npmrc
```

PASS when scripts are off for every listed install after overrides, and someone has reviewed each listed script. Scripts are off when the command passes a bare `--ignore-scripts`, or when `.npmrc` sets `ignore-scripts=true` and nothing from the second grep applies to that install. `--no-ignore-scripts`, `--ignore-scripts=false`, `--ignore-scripts false` and `npm_config_ignore_scripts=false` (any case) all override `.npmrc`; a bare `--ignore-scripts` flag beats the environment variable (checked with npm 11.20.0).

For `.pth` files, use the PyPI `.pth` check in `supply-chain-ecosystem-quirks`.

## Step 4 — Cooldown

Cooldown is the age of each new version at the moment the change that adopted it was merged. The spacing between lockfile commits says nothing about it. Commits ten days apart that each adopt a 90-minute-old release FAIL. Daily commits of week-old releases PASS.

For each version that a lockfile change adds:

```bash
# 1. Publish time, in epoch seconds
#    npm:
pub=$(npm view <package> time --json | jq --arg v '<version>' '.[$v] | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601')
#    PyPI (earliest uploaded file):
pub=$(curl -s https://pypi.org/pypi/<package>/<version>/json | jq '[.urls[].upload_time_iso_8601 | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601] | min')

# 2. Merge time of the change that first added it. Run this on the default
#    branch. <token> is the text the lockfile uses for this version in its file
#    names and URLs. npm and conda keep hyphens (scoped npm packages drop the
#    scope: @scope/name -> name-<version>). Python wheel and sdist names use
#    underscores: pydantic-core 2.50.4 is pydantic_core-2.50.4 in uv.lock and
#    pixi.lock. pnpm-lock.yaml uses <package>@<version>. Check that
#    `grep -c '<token>' <lockfile>` isn't 0.
#    --first-parent -m finds the commit that brought it onto the default branch,
#    not the earlier commit on the feature branch.
sha=$(git log --first-parent -m --reverse --format=%H -S '<token>' -- <lockfile> | head -1)
#    The pull request's merge time, or a merge commit's own time. A commit pushed
#    without a pull request has no merge time and stays UNKNOWN.
adopted=$([ -n "$sha" ] && gh api "repos/{owner}/{repo}/commits/$sha/pulls" \
  --jq '[.[] | select(.merged_at)][0].merged_at // empty | fromdateiso8601' 2>/dev/null)
[ -z "$adopted" ] && [ -n "$sha" ] && git rev-parse -q --verify "$sha^2" >/dev/null \
  && adopted=$(git log -1 --format=%ct "$sha")

# 3. Age at adoption. A missing time means UNKNOWN, never FAIL.
if [ -z "$pub" ] || [ "$pub" = null ] || [ -z "$adopted" ]; then echo UNKNOWN
else echo "$(( (adopted - pub) / 3600 )) hours"; fi
```

FAIL when the age is below the project's cooldown, or below 7 days if it has none. Report UNKNOWN when the publish time or the merge time can't be found, and check that version by hand. Never use the time of the commit on the feature branch: a version committed an hour after publication and merged eight days later meets a 7-day cooldown. Tested on 2026-11-19: that case gives 193 hours (the feature-branch commit time gives 1 hour); a squash-merged pull request on this repository gives its `merged_at`; a commit fast-forwarded without a pull request gives UNKNOWN.

Fix with the update bot's cooldown setting:

- Dependabot, under each `updates` entry in `.github/dependabot.yml`. The days must be 1–90. GitHub's docs say a 3-day default applies to version updates when `cooldown` is unset, and security updates are never delayed.

  ```yaml
      cooldown:
        default-days: 7
  ```

- Renovate. The age comes from the registry's release timestamp; `minimumReleaseAgeBehaviour` decides what happens to a release without one.

  ```json
  { "minimumReleaseAge": "7 days" }
  ```

## Step 5 — Provenance

```bash
grep -rnE --include='*.yml' --include='*.yaml' '(syft|cyclonedx|spdx|cosign|sigstore|--provenance|attest-build-provenance|attest-sbom)' .github/
```

No output from a repository that publishes releases is a FAIL. Fix: the `supply-chain-sbom-provenance` skill.
