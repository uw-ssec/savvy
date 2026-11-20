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

- `supply-chain-hardened-ci-cd`: the description lists only when to use the skill, and the body is restructured around a quick reference, rationalizations and red flags. Every example action is pinned to a commit SHA, including the PyPI publish action that was on `@release/v1`. The OIDC example, which wasn't valid YAML, is now a complete build/publish workflow in `references/hardening-patterns.md`, where the publish job runs no project code: PyPI builds with `PIP_ONLY_BINARY=:all:`, and npm packs the tarball in the build job and publishes it with `--ignore-scripts`.

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
