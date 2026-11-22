# conda / pixi Supply Chain Quirks

## Threat Relevance

The conda ecosystem covers compiled scientific software (CUDA, GDAL, BLAS, etc.) that PyPI wheels often can't provide reproducibly. But conda's trust model is different from npm/PyPI: most packages carry no signature, so trust comes from channel reputation. That makes channel discipline, lockfile use, and the install escape hatches (`--no-deps`, `--no-pin`, `--force-reinstall`) the primary supply-chain controls. The general "verify signatures" advice from `supply-chain-sbom-provenance` usually has nothing to verify for conda packages; document this gap for stakeholders.

## Channel Priority and the defaults Channel Risk

`conda-forge` is the community-governed channel with reviewer-gated PRs and reproducible recipes. `defaults` (Anaconda Inc.) has different governance, different versions, and as of 2024 a commercial license for orgs above a revenue threshold. In conda, `defaults` expands to `default_channels` (`https://repo.anaconda.com/pkgs/main` and `/r`). Pixi has no such alias: `"defaults"` in `pixi.toml` resolves to `https://conda.anaconda.org/defaults/`, which returned 404 when solved with pixi 0.83.0. `pixi init` writes `channels = ["conda-forge"]`.

Channels are a YAML list in `.condarc` and `environment.yml`, but a TOML array in `pixi.toml` (or `[tool.pixi.workspace]` in `pyproject.toml`), so one `grep -A 5 '^channels:'` cannot cover both. `scripts/quick-check.sh` reads both formats and WARNs on `defaults` or a `repo.anaconda.com/pkgs` URL. By hand:

```bash
# Each sed hides user:password@ and /t/<token>/ in channel URLs
conda config --show channels \
  | sed -E 's|://[^/?#[:space:]]*@|://<redacted>@|g; s|/t/[^/[:space:]]+/|/t/<redacted>/|g'   # effective conda channels
grep -nE 'defaults|repo\.anaconda\.com' environment.yml .condarc 2>/dev/null \
  | sed -E 's|://[^/?#[:space:]]*@|://<redacted>@|g; s|/t/[^/[:space:]]+/|/t/<redacted>/|g'
grep -nE -A 5 '^\s*channels\s*=' pixi.toml pyproject.toml 2>/dev/null \
  | sed -E 's|://[^/?#[:space:]]*@|://<redacted>@|g; s|/t/[^/[:space:]]+/|/t/<redacted>/|g'
pixi workspace channel list                                # effective pixi channels
```

If `defaults` is listed, evaluate whether the project can switch to conda-forge only (`nodefaults` in `environment.yml` excludes it):

```bash
conda config --remove channels defaults
conda config --add channels conda-forge
conda config --set channel_priority strict
```

`channel_priority: strict` prevents conda from satisfying a package from a lower-priority channel when a higher-priority channel has it. That closes the dependency-confusion-style attack where a name-squat on a lower channel substitutes for a trusted package.

## pixi.lock vs conda-lock.yml

`pixi` produces a single multi-platform `pixi.lock`. `conda-lock` writes a unified multi-platform `conda-lock.yml` by default (`--kind explicit` writes one `conda-<platform>.lock` per platform). Both encode exact package URLs and hashes; both should be committed.

Lockfile-respecting installs (CI):

```bash
pixi install --locked        # aborts if pixi.lock is out of date with pixi.toml
conda-lock install --name <env> conda-lock.yml
```

Plain `pixi install` rewrites `pixi.lock` when the manifest changed. `pixi install --frozen` installs from `pixi.lock` without checking it against the manifest, so a stale lock passes. Use `--locked` in CI.

## --no-deps and --no-pin (Escape Hatches)

These conda flags bypass solver constraints and lockfiles. Any of them on a `conda`, `mamba` or `micromamba` install, update or create in CI scripts is a P1 finding. (`--no-update-deps` is an alias of `--freeze-installed` and is not an escape hatch. `pip install --no-deps` is a different flag and is common for installing the project itself into a conda env.)

```bash
grep -rnE '(conda|mamba|micromamba) (install|update|create) .*(--no-deps|--no-pin|--force-reinstall)' \
  .github/workflows/ Makefile *.sh 2>/dev/null
```

Legitimate uses are rare, usually a workaround for an unsolvable env. If found, replace with a pinned, lockfile-driven recipe or document the exception in the project README with a justification.

## Signed Channel Verification (the Gap)

Most conda packages carry no signature. conda-content-trust (TUF-based) exists but is experimental and off by default. CEP 27 defines Sigstore attestations for conda packages, and rattler-build generates them when publishing to prefix.dev channels. Whether a given channel attests its packages is channel-specific; it was not confirmed for conda-forge on 2026-11-17. Without an attestation, the trust chain is:

- HTTPS to the channel (transport integrity only)
- Channel's own review process (conda-forge requires PR review, defaults is opaque)
- Per-package `md5`/`sha256` recorded in repodata (channel-attested, not third-party-signed)

This is a real gap versus npm provenance and PyPI's Sigstore attestations. Document it for stakeholders rather than papering over it. Mitigations are channel discipline (above), lockfile pinning, and SBOM generation post-install via `syft <env-path>`.

## pixi run / conda run Sandbox Status

`pixi run <cmd>` and `conda run -n <env> <cmd>` activate the env and execute the command. Neither sandboxes the command: the script has the same filesystem and network access as the shell. Treat any `pixi run` / `conda run` line in CI the same way you'd treat a raw `bash -c`; the env-activation indirection does not add security.

Audit:

```bash
grep -rE '(pixi run|conda run)' .github/workflows/ 2>/dev/null
```

Cross-link to `supply-chain-hardened-ci-cd` for the broader "treat all CI commands as untrusted code execution" pattern.

## References

- conda-content-trust (experimental): <https://github.com/conda/conda-content-trust>
- CEP 27 (conda package attestations): <https://conda.org/learn/ceps/cep-0027>
- pixi lockfile: <https://pixi.sh/latest/workspace/lock_file/>
- conda-forge governance: <https://conda-forge.org/community/governance/>
- channel priority semantics: <https://conda.io/projects/conda/en/latest/user-guide/concepts/installing-with-conda.html#strict-channel-priority>
