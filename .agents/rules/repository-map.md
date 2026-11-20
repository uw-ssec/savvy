# Repository Map

**Load when:** you need to know what this repository is, where a file lives, or
what CI runs against it.

## Repository Overview

**savvy** (`uw-ssec/savvy`, formerly `rse-plugins`) is UW SSEC's marketplace of
agent plugins for research software engineering and scientific computing. Each
plugin bundles skills, and some add agents, commands, and MCP servers. Plugins
follow the [Agent Plugins](https://agent-plugins.org/specification) v1.0.0
format, so they install in Claude Code, GitHub Copilot, Codex, and Cursor, and
their skills also work in Gemini CLI and OpenCode.

Two kinds of agent content live here — keep them apart:

- **Shipped content** — `plugins/` and `community-plugins/`. This is the
  product: users install it, and CI scores and security-scans it.
- **Repo-maintenance content** — `AGENTS.md`, `.agents/rules/`, and
  `.agents/skills/`. These guide agents working _on_ this repository. They are
  not part of any plugin and CI's skill checks do not look at them.

## Project Structure & Key Files

```
.
├── plugins/<plugin>/            # Core plugins (SSEC-maintained)
│   ├── plugin.json              # SOURCE manifest: edit this one
│   ├── .claude-plugin/          # GENERATED plugin.json (pixi run plugins-sync)
│   ├── skills/<skill>/SKILL.md  # Agent Skills; each skill dir is self-contained
│   ├── agents/  commands/       # Claude Code / Cursor only
│   └── README.md
├── community-plugins/<plugin>/  # Community plugins, same layout
├── .claude-plugin/marketplace.json  # SOURCE catalog: plugin list, source, category, strict
├── .agents/
│   ├── plugins/marketplace.json # GENERATED Codex marketplace
│   ├── rules/                   # On-demand rules referenced by AGENTS.md
│   └── skills/                  # Repo-maintenance skills (/commit, /create-pr, ...)
├── .claude/
│   └── skills -> ../.agents/skills  # Symlink so Claude Code discovers the skills
├── .cursor-plugin/marketplace.json  # GENERATED Cursor marketplace
├── .github/
│   ├── scripts/                 # CI scripts (agent_plugins.py, skill_catalog.py, ...) + tests/
│   ├── workflows/               # GitHub Actions (see below)
│   ├── ISSUE_TEMPLATE/          # new_skill.yml
│   └── pull_request_template.md # Includes the AI assistance disclosure
├── .devcontainer/               # Codespaces: Claude Code + Copilot CLI with all plugins
├── docs/
│   ├── catalog.md               # GENERATED skill catalog (pixi run catalog-sync)
│   ├── catalog.yml              # SOURCE: tier, maintainer, example prompt per skill
│   ├── install.md               # Per-client install steps and support matrix
│   ├── trust-and-safety.md
│   └── specs/                   # Design docs and plans (excluded from link checks)
├── evals/                       # Catalog trigger test, dokimi pilot (own pixi.toml)
├── knowledge/                   # OKF project memory, managed by the okf CLI (okf-memory skill)
├── pixi.toml / pixi.lock        # Environments and tasks; never edit the lock by hand
├── lychee.toml                  # External link check config
├── AGENTS.md  CLAUDE.md         # Agent entry point; CLAUDE.md is just @AGENTS.md
├── AI_POLICY.md                 # AI disclosure and the Assisted-by trailer
├── CONTRIBUTING.md              # Plugin conventions, catalog, evals, security review checklist
└── README.md  SECURITY.md  CITATION.cff  LICENSE
```

`CONTRIBUTING.md` is the authority on plugin conventions — which files are
generated, keeping skills self-contained, `mcp.json` vs `.mcp.json`, agent
`skills:` as a list, and string-valued skill `metadata`. Read its "Plugin
Manifests and Other Clients" section before editing any plugin.

## Continuous Integration

| Workflow                  | Runs on                                       | What it does                                                                                                                                               |
| ------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate-plugins.yml`    | PRs touching plugins, manifests, docs, `*.md` | `plugins-check`, `catalog-check`, Agent Plugins JSON schemas, `claude plugin validate --strict`, duplicate JSON keys, structure and security pattern scans |
| `skill-quality-check.yml` | PRs touching a plugin skill                   | SkillEvaluator `quality-check` on each changed skill; fails below 70                                                                                       |
| `test-ci-scripts.yml`     | PRs touching `.github/scripts/` or workflows  | `pixi run test-scripts`                                                                                                                                    |
| `zizmor.yml`              | PRs touching `.github/workflows/`             | Workflow security lint                                                                                                                                     |
| `check-links.yml`         | Push to `main` (Markdown), weekly             | `pixi run links-check` (lychee, external URLs only)                                                                                                        |
| `evaluate-*.yml`          | Manual                                        | Skill evals against the private testcases repo                                                                                                             |
| `generate-testcases.yml`  | Manual                                        | Drafts testcases for skills a PR adds                                                                                                                      |

CI pins `pixi-version: v0.82.0`. Regenerate `pixi.lock` with that version so the
lock file doesn't churn.

## Further Reading

For more information on SSEC best practices, see:
https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt
