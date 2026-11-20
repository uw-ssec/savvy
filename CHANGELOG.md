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
- `supply-chain-ecosystem-quirks`: `scripts/quick-check.sh` runs the npm, PyPI, conda/pixi, cargo and Go checks and reports each finding with its `file:line`. Its `--pth-only` mode is the canonical Python `.pth`/`.start` startup-code check that other supply-chain skills point to: known-good files are INFO only when name and content match what their tool writes, and unknown code-executing files FAIL.

#### Changed

- `supply-chain-ecosystem-quirks`: the description is trigger-only, and the quick-check battery moves from `SKILL.md` into the script.

#### Fixed

- `supply-chain-ecosystem-quirks`: references corrected against current tools: npm 12's `allowScripts`, pnpm's `allowBuilds` and Yarn 4.14's `enableScripts` default; `uv sync --locked`, `pixi install --locked` and `poetry check --lock` in place of flags that skip the lockfile check or don't exist; Go's `-mod=readonly` is already the default, so `-mod=mod` is flagged instead; the removed `-insecure` flag; `Cargo.lock` guidance; and the PyTorch-nightly compromise no longer attributed to `setup.py`.

### uiux-design-team

#### Added

- Initial tagged release.

### zarr-chunk-optimization

#### Added

- Initial tagged release.

### zarr-data-format

#### Added

- Initial tagged release.

### Repository

#### Added

- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).
