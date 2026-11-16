# Security Policy

This repository publishes plugins (skills, agents, commands and MCP server configurations) that AI coding agents load and act on. A security problem here can mean ordinary vulnerable code, but it can also mean instructions that lead an agent to do something harmful. Both are in scope.

For what plugins can and can't do once installed, and how to review one before you install it, see [Trust and safety](docs/trust-and-safety.md).

## Supported versions

Releases use calendar versions, starting with `v26.11.0` (see [Releases](https://github.com/uw-ssec/savvy/releases)). We fix security problems on `main` and in the latest release only:

| Version | Supported |
| --- | --- |
| Latest commit on `main` | ✅ |
| Latest release | ✅ Fixes ship as a new point release |
| Older releases, older commits, and copies made before a fix | ❌ |

A fix changes the affected plugin's `version` in its `plugin.json` to the release that contains the fix, so clients that compare versions will offer the update. You won't get a fix automatically if you pinned a release tag or copied a plugin by hand (Cursor, OpenCode or a skills directory). Move to the new release, or copy the plugin again.

To hear about fixes, watch the repository with **Watch → Custom → Security alerts**. Each fix is also listed under **Security** in the release notes and in `CHANGELOG.md`.

## Reporting a vulnerability

**Please don't report security problems in public issues, pull requests or discussions.**

Report privately through GitHub: go to [Report a vulnerability](https://github.com/uw-ssec/savvy/security/advisories/new) on the repository's **Security** tab. Only the maintainers can see the report, and we can work on a fix with you in a private fork.

If you can't use GitHub's private reporting, open a public issue that says only that you have a security report and want a private contact. Don't include any details. A maintainer will reply with a way to reach us.

Please include:

- The affected plugin and file path (for example `plugins/<plugin>/skills/<skill>/SKILL.md`), and the commit you looked at
- What the problem is, and what an attacker or a misled agent could do with it
- The agent client and version you used to reproduce it (for example Claude Code, GitHub Copilot CLI, VS Code, Codex, Gemini CLI, Cursor or OpenCode), with the prompt or steps
- Any fix you'd suggest

## What to expect

| Step | Target |
| --- | --- |
| We acknowledge your report | Within 5 business days |
| We confirm or decline it and tell you our assessment | Within 10 business days of acknowledging |
| We fix it, or remove the affected plugin, skill or command until we can | Within 30 days for high-severity issues; otherwise in a normal release |

These are targets, not guarantees; the maintainers are a small team. We'll keep you informed while we work on it. When the fix is released, we publish a GitHub security advisory and, if you want, credit you in it.

Removing a plugin, skill or command for a security reason doesn't wait for the usual deprecation notice period. We remove or disable it right away and announce it in the advisory, the release notes and `CHANGELOG.md`.

Please give us a reasonable time to fix the problem before you disclose it publicly, and don't test against other people's machines, accounts or data.

## Scope

In scope, for plugins in both the Core and Community tiers:

- **Harmful or hidden instructions** in a skill, agent, command or reference file: prompt injection, text hidden from human reviewers (HTML comments, invisible Unicode, encoded payloads), or instructions that tell the agent to bypass its permission prompts, disable safety settings, or hide what it's doing
- **Unsafe commands** that a skill, agent or command tells the agent to run, such as piping a download into a shell, deleting outside the project, or changing credentials or system settings without saying so
- **Data exfiltration**: instructions or bundled scripts that send code, secrets or data to a destination the user didn't ask for
- **Over-broad tool grants**, such as an `allowed-tools` entry that pre-approves more than the skill, command or agent needs
- **Bundled scripts and MCP configurations** in this repository, including MCP servers that point to compromised or unexpected packages or images
- **This repository's CI**: GitHub Actions workflows, the scripts in `.github/scripts`, and the handling of secrets

Out of scope (please report these elsewhere):

- Vulnerabilities in an agent client itself. Report them to its vendor, such as Anthropic, GitHub, Microsoft, OpenAI, Google, Cursor or the OpenCode project.
- Vulnerabilities in third-party software that a plugin installs or starts, such as a Python package or the HoloViz MCP container image. Report them upstream. If one of our plugins makes the problem worse, for example by pointing to an unpinned version, tell us too.
- A model making a mistake that isn't caused by our content. General model misbehavior belongs with the model provider.
- Inaccurate or outdated technical guidance with no security impact. Open a normal issue for that.
