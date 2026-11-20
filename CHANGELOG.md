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

#### Changed

- `supply-chain-threat-awareness`: the description lists triggers only, and the audit commands moved to `references/audit-commands.md`. Each campaign now has the dates it was observed and primary sources; Shai-Hulud is described as a self-propagating worm with a second wave in November 2025, and TeamPCP as running from March to April 2026.

#### Fixed

- `supply-chain-threat-awareness` and `/supply-chain-audit`: the action-pinning scan flags every mutable `uses:` ref, including `.yaml` files, local composite actions anywhere in the repository, untracked files, flow-style and quoted-key YAML, `docker://` tags and SHA-prefixed branches.
- `supply-chain-threat-awareness`: cooldown is measured as each version's age when the change adopting it was merged, locked installs require `--locked`, the lifecycle-script query lists all eight hooks npm runs for the project on install, and the LiteLLM check no longer runs `pip show` in the suspect environment.

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
