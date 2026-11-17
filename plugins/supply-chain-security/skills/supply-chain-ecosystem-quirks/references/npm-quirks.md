# npm / yarn / pnpm Supply Chain Quirks

## Threat Relevance

npm's install-time script execution is the single most-exploited supply-chain vector in the JavaScript ecosystem. The Shai-Hulud worm propagates via `postinstall` scripts; the `ua-parser-js`, `coa`, and `rc` compromises all executed payloads at `npm install` time before any project code ran. Whether dependency scripts run by default now depends on the package manager and its version (below). Lockfile discipline, registry-proxy config, and provenance attestations are the other config knobs that decide whether the general "pin and scan" advice from `supply-chain-dependency-security` actually holds for a Node project.

## Install-Time Script Execution

npm 11 and older run `preinstall`, `install`, and `postinstall` scripts from every dependency, transitively. This is the Shai-Hulud landing zone. npm 12 (July 2026) blocks dependency install scripts unless `package.json` approves them under `allowScripts` (`npm install-scripts approve <package>`). The install still exits 0 and lists the skipped packages. CI often runs an older npm (conda-forge's Node 26 ships npm 11.20.0), so set one of these regardless of version.

Disable globally via `.npmrc`:

```bash
echo "ignore-scripts=true" >> .npmrc
grep -qE '^\s*ignore-scripts\s*=\s*true' .npmrc && echo "PASS: scripts disabled"
```

Or per-command in CI:

```bash
npm ci --ignore-scripts
```

Either one passes. `scripts/quick-check.sh` judges each CI install by its effective value, in npm's order: command line, then `npm_config_ignore_scripts` in that CI file, then `.npmrc`. `--ignore-scripts=false`, `--ignore-scripts false`, `--no-ignore-scripts` or `npm_config_ignore_scripts=false` (any case) re-enable scripts despite `.npmrc` (verified on npm 11.20.0); a bare `--ignore-scripts` still wins over the variable. Comments don't count. On npm 12, `ignore-scripts=true` in `.npmrc` overrides `allowScripts`: `npm rebuild <package>` reports success but runs nothing. To build one reviewed package, run `npm rebuild <package> --ignore-scripts=false`.

## .npmrc Knobs That Affect Security

Audit `.npmrc` (project root and `~/.npmrc`) for these settings. Each line below is the desired state plus the verifying command.

- `package-lock` defaults to `true`; flag an explicit `package-lock=false`.
  `grep -qE '^\s*package-lock\s*=\s*false' .npmrc && echo "FAIL: lockfile disabled"`
- `audit-level=high` or `critical`: fail `npm audit` on real issues only.
  `grep -E 'audit-level=(high|critical)' .npmrc`
- `fund=false`: suppresses funding-prompt noise that hides real warnings.
  `grep -q 'fund=false' .npmrc`
- `save-exact=true`: defaults installs to exact versions instead of `^x.y.z` ranges.
  `grep -q 'save-exact=true' .npmrc`
- `engine-strict=true`: refuses installs on the wrong Node version.
  `grep -q 'engine-strict=true' .npmrc`

## npm ci vs npm install

`npm ci` requires `package-lock.json` to exist and refuses to modify it; it deletes `node_modules/` first and installs exactly what the lock specifies. `npm install` will silently rewrite the lockfile to match new ranges in `package.json` if it finds satisfying versions. In CI, always use `npm ci`. The failure mode if you don't:

```bash
# in CI, this silently upgrades patches across the dep tree
npm install        # BAD: rewrites package-lock.json, defeats pin discipline
npm ci             # GOOD: respects the lockfile, fails if lock is out of sync
```

Verify CI uses `npm ci`: `grep -rnE '(^|[^[:alnum:]])npm (install|i)( |$)' .github/workflows/`.

## npm Provenance Attestations

`npm publish --provenance` (npm 9.5.0+) generates a Sigstore attestation tied to the GitHub Actions workflow that built the package. The attestation is uploaded to the public Sigstore Rekor log and displayed on the npm registry page.

```bash
# In a publish job with permissions: id-token: write
npm publish --provenance --access public
```

Verify a consumed package:

```bash
npm audit signatures
```

Cross-link: see `supply-chain-sbom-provenance` for the full Sigstore/SLSA story and `references/sigstore-cookbook.md` in that skill for the `permissions:` block.

## pnpm and Yarn Specifics

`pnpm` uses a content-addressable store with symlinks: no flat `node_modules/`, and each package only sees its direct deps. This kills the implicit-dependency attack class (a transitive can't be `require()`'d unless declared).

pnpm lifecycle scripts by version:

- pnpm 10.0.0 (January 2025) stopped running dependency lifecycle scripts by default. The allowlist was `pnpm.onlyBuiltDependencies` in `package.json`.
- pnpm 11.0.0 (April 2026) removed `onlyBuiltDependencies` and no longer reads the `pnpm` field in `package.json`. Approvals live in `allowBuilds` in `pnpm-workspace.yaml`, written by `pnpm approve-builds <package>`. An unapproved build script fails the install with `ERR_PNPM_IGNORED_BUILDS` (tested on pnpm 12.21.0).

```yaml
# pnpm-workspace.yaml
allowBuilds:
  esbuild: true
```

Yarn scripts by version:

- Yarn 4.14.0 (April 2026) made `enableScripts: false` the default in `.yarnrc.yml`, so third-party `postinstall` scripts are skipped. Workspace scripts still run.
- Yarn 2 to 4.13 run dependency scripts unless `enableScripts: false` is set.
- Yarn classic (1.x) runs them unless `--ignore-scripts` is passed.

Both pnpm and current Yarn reduce install-time-script attack surface versus npm 11 and older. Recommend either when the project is willing to migrate.

## References

- npm config: <https://docs.npmjs.com/cli/v10/configuring-npm/npmrc>
- npm provenance: <https://docs.npmjs.com/generating-provenance-statements>
- pnpm build settings (`allowBuilds`): <https://pnpm.io/settings>
- pnpm 11 release notes: <https://pnpm.io/blog/releases/11.0>
- Yarn `enableScripts`: <https://yarnpkg.com/configuration/yarnrc#enableScripts>
- Shai-Hulud writeup: cross-link to `supply-chain-threat-awareness`
