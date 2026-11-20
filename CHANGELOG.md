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

#### Fixed

- Fixed broken links in the `supply-chain-ecosystem-quirks` skill references, refs #249.

### uiux-design-team

#### Added

- Initial tagged release.

### zarr-chunk-optimization

#### Added

- Initial tagged release.

#### Fixed

- Fixed the broken DOI and title for the Nguyen et al. (2023) paper cited in the README, refs #249.

### zarr-data-format

#### Added

- Initial tagged release.

### Repository

#### Added

- `CHANGELOG.md`, a [versioning policy](docs/versioning.md), and a [deprecation policy](docs/deprecation.md).

#### Fixed

- Fixed the broken Claude Code link in the root `README.md`, refs #249.
- Removed the `lychee.toml` link-check exclusions for the links fixed in #249 and the `softwareheritage.org` TLS workaround; only `vizier.cds.unistra.fr` stays excluded, with the reason noted.
