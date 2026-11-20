# savvy

[![Validate Plugins](https://github.com/uw-ssec/savvy/actions/workflows/validate-plugins.yml/badge.svg?branch=main)](https://github.com/uw-ssec/savvy/actions/workflows/validate-plugins.yml?query=branch%3Amain)
[![Test CI scripts](https://github.com/uw-ssec/savvy/actions/workflows/test-ci-scripts.yml/badge.svg?branch=main)](https://github.com/uw-ssec/savvy/actions/workflows/test-ci-scripts.yml?query=branch%3Amain)
[![DOI](https://zenodo.org/badge/1091290859.svg)](https://zenodo.org/badge/latestdoi/1091290859)
[![License: BSD-3-Clause](https://img.shields.io/github/license/uw-ssec/savvy)](LICENSE)
[![Pixi Badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/uw-ssec/savvy?quickstart=1)

savvy is a collection of plugins that help AI coding assistants with research software engineering and scientific computing, so the code they help write follows the practices the Scientific Python community already uses. The plugins cover environments with pixi, packaging, testing, documentation, containers, supply-chain security, research workflows, and project handoff, along with domain work in astronomy, climate and Earth science, Zarr, and interactive visualization with HoloViz. Each plugin bundles skills (instructions the assistant loads when a request matches them), and many add agents and commands for Claude Code.

## Install

In Claude Code:

```bash
claude plugin marketplace add uw-ssec/savvy
claude plugin install scientific-python-development@savvy
```

Skills also work in GitHub Copilot (CLI and VS Code), Codex, Cursor, Gemini CLI, and OpenCode. [docs/install.md](docs/install.md) has the support matrix and install steps for each client. To try everything without installing, open a Codespace with the badge above; [docs/codespaces.md](docs/codespaces.md) covers routing Copilot through your own LiteLLM gateway.

> [!IMPORTANT]
> Skills are instructions, not programs, but your agent acts on them: it may run commands, edit files and use the network, within the permissions your client allows. Before installing, read [Trust and safety](docs/trust-and-safety.md) for what plugins can and can't do, how to review one, and where each client's permission controls are. To report a security problem privately, see [SECURITY.md](SECURITY.md).

## Find a skill

The [skill catalog](docs/catalog.md) lists every plugin, skill, command, and agent on one page, with the phrases that trigger each skill, an example prompt to try, and who maintains it. The plugins themselves live in [plugins/](plugins/) and [community-plugins/](community-plugins/), and each has its own README.

## Documentation

- [Installation](docs/install.md): which clients load which parts of a plugin, and how to install in each
- [Skill catalog](docs/catalog.md): every skill, command, and agent, grouped by plugin and tier
- [Codespaces](docs/codespaces.md): the preconfigured Codespace and the optional LiteLLM gateway
- [Trust and safety](docs/trust-and-safety.md): what plugins can and can't do, and how to review one before installing
- [Versioning policy](docs/versioning.md): how releases and plugin versions are numbered
- [Deprecation policy](docs/deprecation.md): the notice you get before a skill, command, agent, or plugin changes or disappears
- [Changelog](CHANGELOG.md): what changed in each release
- [Contributing](CONTRIBUTING.md): plugin conventions, evals, and the security review checklist every plugin change must pass
- [AI policy](AI_POLICY.md): what we ask of AI-assisted contributions
- [Security policy](SECURITY.md): how to report a vulnerability privately, response times, and supported versions

## How to cite

If you use savvy in your research, please cite it. The **Cite this repository** button in the repository sidebar gives APA and BibTeX, generated from [CITATION.cff](CITATION.cff).

Each GitHub Release is archived on Zenodo with a DOI. The DOI badge at the top of this page links to the latest release's DOI once the first release is published.

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Developed and maintained by the University of Washington Scientific Software Engineering Center (UW-SSEC).

## Questions or Issues?

Please open an issue on [GitHub](https://github.com/uw-ssec/savvy/issues). Report security problems privately as described in [SECURITY.md](SECURITY.md), not in a public issue.
