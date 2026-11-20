# Changelog

All notable changes to this repository are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository follows the [versioning policy](docs/versioning.md) — Ubuntu-style Calendar Versioning, with each plugin's manifest version set to the release in which that plugin last changed.

## How to add an entry

Add your entry under `## [Unreleased]`, inside the `###` subsection for the plugin you changed. Use the Keep a Changelog categories as `####` headings: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.

A `Deprecated` entry must say what replaces the deprecated thing — or state that nothing does, and why — and give the earliest removal date, as required by the [deprecation policy](docs/deprecation.md).

Changes that touch no plugin — CI, repository documentation, tooling — go under [Repository](#repository) rather than a plugin subsection.

## [Unreleased]

First tagged release. Plugin versions move to this release for every plugin below.

### ai-research-workflows

#### Added

- Initial tagged release.
- Capability metadata, a skill card and a public eval task set on each skill, as part of the skill trust evidence pilot ([#293](https://github.com/uw-ssec/savvy/issues/293)).

### containerization

#### Added

- Initial tagged release.

### gaia-data-downloader

#### Added

- Initial tagged release.

### holoviz-visualization

#### Added

- Initial tagged release.

### project-management

#### Added

- Initial tagged release.

### research-software-design

#### Added

- Initial tagged release.

### scientific-domain-applications

#### Added

- Initial tagged release.

### scientific-python-development

#### Added

- Initial tagged release.

### supply-chain-security

#### Added

- Initial tagged release.

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

- Skill trust evidence pilot for `ai-research-workflows` ([#293](https://github.com/uw-ssec/savvy/issues/293)): a skill card and a public eval task set (`evals/evals.json`) for each skill, a manually run benchmark workflow (`BENCHMARK.md`, reported and never gating), and per-skill archives signed with Sigstore by `release-sign.yml` when a release is published. These files don't count as plugin changes for [versioning](docs/versioning.md). See [Checking a skill before you install it](docs/trust-and-safety.md#checking-a-skill-before-you-install-it) and [Signed skill archives](docs/releasing.md#signed-skill-archives). Signing starts with the first release cut after this change merges, and the `release` skill no longer builds an unsigned zip for `ai-research-workflows`.
- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).
- [docs/codespaces.md](docs/codespaces.md), with the Codespaces and LiteLLM gateway setup moved out of the README.
- README badges for CI, the Zenodo DOI, the license, and pixi.

#### Changed

- The README is shorter and points to the [skill catalog](docs/catalog.md) and the other docs instead of listing every plugin, skill, and agent itself.
- [docs/install.md](docs/install.md) and [docs/trust-and-safety.md](docs/trust-and-safety.md) cover Antigravity CLI instead of Gemini CLI, which Google retired for most users in June 2026. Each plugin README's note on client support now says which parts Antigravity CLI loads.
