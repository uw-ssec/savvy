# Changelog

All notable changes to this repository are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository follows the [versioning policy](docs/versioning.md) — Ubuntu-style Calendar Versioning, with each plugin's manifest version set to the release in which that plugin last changed.

## How to add an entry

Add your entry under `## [Unreleased]`, inside the `###` subsection for the plugin you changed. Use the Keep a Changelog categories as `####` headings: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.

A `Deprecated` entry must say what replaces the deprecated thing — or state that nothing does, and why — and give the earliest removal date, as required by the [deprecation policy](docs/deprecation.md).

Changes that touch no plugin — CI, repository documentation, tooling — go under [Repository](#repository) rather than a plugin subsection.

## [Unreleased]

First tagged release. Only `ai-research-workflows` ships in it and moves to this release's version. The other plugins below are marked `released: false` in [docs/catalog.yml](docs/catalog.yml) until they are ready, so no marketplace lists them yet and their entries wait for the release that ships them.

### ai-research-workflows

#### Added

- Initial tagged release.

### containerization

#### Added

- Initial tagged release.

### gaia-data-downloader

#### Added

- Initial tagged release.

### holoviz-visualization

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken HoloViz, Panel, Lumen, hvPlot, and Param documentation links in the README and the `colormaps-styling`, `lumen-ai`, `lumen-dashboards`, and `parameterization` skills, refs #249.

### project-management

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken links in the `community-health-files` and `documentation-validation` skill references, refs #249.

### research-software-design

#### Added

- Initial tagged release.

### scientific-domain-applications

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken rioxarray and Geocube documentation links in the README, refs #249.

### scientific-python-development

#### Added

- Initial tagged release.

#### Fixed

- Fixed broken links in the `scientific-documentation` skill references, refs #249.

### supply-chain-security

#### Added

- Initial tagged release.
- `supply-chain-ecosystem-quirks`: `scripts/quick-check.sh` runs the npm, PyPI, conda/pixi, cargo and Go checks and reports each finding with its `file:line`. Its `--pth-only` mode is the canonical Python `.pth`/`.start` startup-code check that other supply-chain skills point to: known-good files are INFO only when name and content match what their tool writes, and unknown code-executing files FAIL.

#### Changed

- `supply-chain-dependency-security`: the description lists triggers only and leaves reported compromises to `supply-chain-incident-response`. CI install commands now fail on a stale lockfile (`pixi install --locked`, `uv sync --locked`, and a `--check-input-hash` step for conda-lock), and Yarn disables install scripts explicitly. The 7-day cooldown gains a resolver setting per tool and a publish-time check for versions a lockfile diff adds. The skill now has When to Use, Quick Reference, rationalization, red-flag and Common Mistakes sections.
- `supply-chain-ecosystem-quirks`: the description is trigger-only, and the quick-check battery moves from `SKILL.md` into the script.
- `supply-chain-ecosystem-quirks`: `scripts/quick-check.sh` builds `file:line` with parameter expansion instead of a nested `printf` and `cut`, which SkillSpector's shell parser could not resolve. Its output is unchanged.
- `supply-chain-hardened-ci-cd`: the description lists only when to use the skill, and the body is restructured around a quick reference, rationalizations and red flags. Every example action is pinned to a commit SHA, including the PyPI publish action that was on `@release/v1`. The OIDC example, which wasn't valid YAML, is now a complete build/publish workflow in `references/hardening-patterns.md`, where the publish job runs no project code: PyPI builds with `PIP_ONLY_BINARY=:all:`, and npm packs the tarball in the build job and publishes it with `--ignore-scripts`.
- `supply-chain-threat-awareness`: the description lists triggers only, and the audit commands moved to `references/audit-commands.md`. Each campaign now has the dates it was observed and primary sources; Shai-Hulud is described as a self-propagating worm with a second wave in November 2025, and TeamPCP as running from March to April 2026.

#### Fixed

- `supply-chain-ecosystem-quirks`: references corrected against current tools: npm 12's `allowScripts`, pnpm's `allowBuilds` and Yarn 4.14's `enableScripts` default; `uv sync --locked`, `pixi install --locked` and `poetry check --lock` in place of flags that skip the lockfile check or don't exist; Go's `-mod=readonly` is already the default, so `-mod=mod` is flagged instead; the removed `-insecure` flag; `Cargo.lock` guidance; and the PyTorch-nightly compromise no longer attributed to `setup.py`.
- `supply-chain-threat-awareness` and `/supply-chain-audit`: the action-pinning scan flags every mutable `uses:` ref, including `.yaml` files, local composite actions anywhere in the repository, untracked files, flow-style and quoted-key YAML, `docker://` tags and SHA-prefixed branches.
- `supply-chain-threat-awareness`: cooldown is measured as each version's age when the change adopting it was merged, locked installs require `--locked`, the lifecycle-script query lists all eight hooks npm runs for the project on install, and the LiteLLM check no longer runs `pip show` in the suspect environment.
- Fixed broken links in the `supply-chain-ecosystem-quirks` skill references, refs #249.
- `supply-chain-incident-response`: the description is now trigger-only, and commands that did nothing or reported a false PASS are replaced: the advisory lookup, lockfile grep and history, `gh cache` listing and deletion by id, `find -newermt`, the postinstall query and the tag-hijack audit loop. Recovery re-enables the disabled workflows and starts a fresh run from the fixed commit. The npm rotation creates a granular, package-scoped token with an expiry (npm 11.6.3 or later, or npmjs.com for older clients).
- `/supply-chain-incident` is now user-invoked only (`disable-model-invocation: true`), so incident prompts load `supply-chain-incident-response` instead of the command, and its paths to the rotation guide and report template now go through the skill.

#### Security

- `supply-chain-incident-response`: the persistence hunt read `.npmrc` with `cat`, which printed auth tokens into the terminal and the agent transcript. It now replaces `_auth`, `_authToken` and `_password` values (quoted keys included) and `user:password@` in URLs with `<redacted>`. The rotation runbook sets GitHub secrets at `gh secret set`'s prompt instead of with `--body`, which put the value in shell history. It warns that `gh` given no input sets an empty secret. New AWS and Azure keys go to a new owner-only file (`umask 077`) instead of the terminal. The Azure reset uses `--append`, so the old secret stays valid until it is deleted, as the rotation order requires. `npm token create` prints the new token, so the runbook says to run it outside an agent. The PyPI step no longer calls a TestPyPI upload a no-op dry run: TestPyPI uses separate tokens and any upload publishes, so the old token is now revoked after a release succeeds with the new one.
- `supply-chain-ecosystem-quirks`: the conda channel and `go env` checks redact `user:password@` in URLs and conda `/t/<token>/` paths. `conda config --show channels` and `go env` otherwise print URL credentials verbatim. The cargo registry check printed `token` values with `grep -A 2`. It now parses `.cargo/config.toml` as TOML, shows a token only as `<set>`, and redacts URL credentials, so multi-line strings and inline tables don't leak either.

### uiux-design-team

#### Added

- Initial tagged release.

### zarr-chunk-optimization

#### Added

- Initial tagged release.

#### Changed

- `access-pattern-analysis`: each pattern now records the `--slice-dims`/`--traverse-dims` arguments `benchmark_runner.py` actually takes, and the skill checks coordinate order and longitude convention before writing any `sel()`. The description is now trigger-only.
- `access-pattern-analysis`: corrects the example byte counts, chunk-shape recommendations (now ~1 MB), sharding and Kerchunk/VirtualiZarr claims, and outdated pandas/xarray calls (`resample("1M")`, `DataArray.visualize()`).
- `rechunking` works under zarr-python 3, where `rechunker` can't be installed: it routes single arrays, sharded targets, flat groups and nested groups to `zarr.from_array`, xarray or dask, and its description is trigger-only.
- `rechunking` validation examples run on Zarr v3 stores and compare values exactly, with NaN treated as equal in float and complex data, instead of checking shape alone.

#### Fixed

- `chunking-strategy`: benchmark each candidate as its own rechunked store, since `benchmark_runner.py` only labels results with `--configs` and never applies them. Also corrects the time-series `--traverse-dims` flag, the rechunk example (stale `encoding["chunks"]`), `sel` vs `isel` on datetime coordinates, the overhead, cost and memory arithmetic, KB-sized "optimal" chunks, zarr 2-only APIs, and the statistics guidance.
- `chunking-strategy`: the description is now trigger-only ("Use when ...").
- `performance-reporting` now reads the JSON that `benchmark_runner.py` actually writes, with a tested loader, and stops reporting TTFB and chunk utilization, which the runner never measures.
- `performance-reporting` drops the weighted pattern-bias score, which rated equal times as unbalanced, and corrects the example numbers, table sorting and ranking rules to match `chunking-strategy`.
- Fixed the broken DOI and title for the Nguyen et al. (2023) paper cited in the README, refs #249.

### zarr-data-format

#### Added

- Initial tagged release.

#### Changed

- `zarr-fundamentals`: the description now says only when to use the skill, and no longer covers the cloud, codec, migration and xarray topics that belong to sibling skills.
- `compression-codecs`: rewritten for zarr 3. Examples use `compressors=[zarr.codecs...]` and `zarr.codecs.numcodecs` filters instead of the v2 `compressor=` and numcodecs filters that raise on v3 arrays (v2 is kept as an explicit `zarr_format=2` path), invented compression ratios are replaced with measured ones, and the description is now trigger-only.
- `compression-codecs`: `assets/codec-comparison.py` now benchmarks through zarr on real or supplied data, and the skill corrects filter order (Quantize before Delta), uses `Crc32cCodec`/Zstd checksums for integrity checks, and drops the unsupported Blosc fork-corruption claim.
- `data-migration`: the description is trigger-only, and a Zarr v2 to v3 route is added. `zarr.copy` (`NotImplementedError` in zarr 3) and `rechunker` (needs `zarr<3`) are dropped in favor of `zarr-chunk-optimization:rechunking`.

#### Fixed

- `zarr-fundamentals`: examples and advice now match zarr-python 3. The sharding example no longer swaps chunks and shards, `resize` takes a tuple, the removed synchronizers give way to a one-writer-per-chunk (or shard) rule, and the quickstart script runs without `rich` and removes its temp directory.
- `zarr-xarray-integration`: encoding examples and the bundled round-trip script now pass `chunks` as a tuple, which xarray requires, and drop stale chunk encoding before rechunked writes. Append and region-write recipes now avoid silent data damage, and the guidance on consolidated metadata, `open_zarr` chunk defaults and `compressors=` codecs is corrected. The description now says only when to use the skill.
- `cloud-storage-backends`: rewrite the Icechunk examples for the current `Repository` and session API (the 0.1 `StorageConfig`/`IcechunkStore` API no longer exists), document which fsspec and zarr caches actually work with `FsspecStore`, and correct the CMIP6 example, the `zarr[remote]` extra, GCS anonymous access, v3 consolidated metadata, slow-open causes and broken helper snippets.
- `cloud-storage-backends`: replace hard-coded MinIO, Azure and AWS credentials in the examples with environment variables, profiles or managed identity.
- `data-migration`: recipes that corrupted data with no error. `encoding=` now keeps packing, fill values, `missing_value` and `_Unsigned` data; appended finer time steps get correct dates; kerchunk merges keep every file's times; and validation compares attribute values, including global attributes, without loading whole arrays. The VirtualiZarr 2.x, Icechunk and h5py code runs on current releases.

### Repository

#### Added

- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).
- [docs/codespaces.md](docs/codespaces.md), with the Codespaces and LiteLLM gateway setup moved out of the README.
- README badges for CI, the Zenodo DOI, the license, and pixi.
- `released: false` in [docs/catalog.yml](docs/catalog.yml) holds a plugin back from a release: no marketplace lists it and the [skill catalog](docs/catalog.md) leaves it out, while CI still checks it. Every plugin except `ai-research-workflows` is held back for now.

#### Changed

- The README is shorter and points to the [skill catalog](docs/catalog.md) and the other docs instead of listing every plugin, skill, and agent itself.
- [docs/install.md](docs/install.md) and [docs/trust-and-safety.md](docs/trust-and-safety.md) cover Antigravity CLI instead of Gemini CLI, which Google retired for most users in June 2026. Each plugin README's note on client support now says which parts Antigravity CLI loads.

#### Fixed

- Removed the `lychee.toml` link-check exclusions for the links fixed in #249 and the `softwareheritage.org` TLS workaround; `vizier.cds.unistra.fr` stays excluded, with the reason noted, as do the README's Zenodo DOI badge links until the first release is archived.
