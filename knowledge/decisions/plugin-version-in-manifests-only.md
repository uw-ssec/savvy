---
type: Decision
title: Plugin versions live only in plugin manifests
description: "A plugin's version is set only in its plugin.json manifests: never in marketplace entries, and the marketplace has no version of its own."
tags: [versioning, marketplace, plugins, release]
generated: { by: "claude-code:claude-opus-5-5", at: "2026-11-18T18:09:38Z" }
status: stable
governance: constraint
code_refs: [".github/scripts/agent_plugins.py", ".claude-plugin/marketplace.json"]
sources: ["https://github.com/uw-ssec/savvy/issues/289", "https://code.claude.com/docs/en/plugins/host-marketplace.md", "https://code.claude.com/docs/en/plugins/loading.md", "https://agent-plugins.org/specification"]
---

## Decision

A plugin's `version` lives only in `<plugin>/plugin.json` and the `.claude-plugin/plugin.json` that `plugins-sync` generates from it.
- `plugins-sync` writes no `version` into `.claude-plugin/marketplace.json` entries (#289), and `plugins-check` treats one added by hand as drift.
- The marketplace has no top-level `version` either.

## Why

- Claude Code takes a plugin's version from `plugin.json` first, then the marketplace entry, then the commit SHA. It installs a new copy only when that value changes. An entry version is ignored while `plugin.json` sets one, and `claude plugin validate` warns when the two differ.
- No client uses a marketplace-level version for updates. The release version lives in the git tag and `CITATION.cff`.
- Users pin a release with a git ref, not a version field. Examples: `claude plugin marketplace add uw-ssec/savvy#v26.11.0`, or Codex's `owner/repo@ref` and `--ref`.

## Consequence

A plugin whose files change but whose `version` doesn't is never updated for Claude Code users. Every release must bump the version of each plugin that changed (versioning policy in #258, first release in #287).

## Sources

- Claude Code docs:
  - "Host and maintain a marketplace", section Release a new version: https://code.claude.com/docs/en/plugins/host-marketplace.md
  - "Plugin loading reference", section Versions and updates: https://code.claude.com/docs/en/plugins/loading.md
  - "Marketplace reference": https://code.claude.com/docs/en/plugins/marketplace-reference.md
- Agent Plugins specification §5.4 and §10.2: https://agent-plugins.org/specification
