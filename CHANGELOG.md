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

### zarr-data-format

#### Added

- Initial tagged release.

#### Changed

- `compression-codecs`: rewritten for zarr 3. Examples use `compressors=[zarr.codecs...]` and `zarr.codecs.numcodecs` filters instead of the v2 `compressor=` and numcodecs filters that raise on v3 arrays (v2 is kept as an explicit `zarr_format=2` path), invented compression ratios are replaced with measured ones, and the description is now trigger-only.
- `compression-codecs`: `assets/codec-comparison.py` now benchmarks through zarr on real or supplied data, and the skill corrects filter order (Quantize before Delta), uses `Crc32cCodec`/Zstd checksums for integrity checks, and drops the unsupported Blosc fork-corruption claim.

### Repository

#### Added

- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).
