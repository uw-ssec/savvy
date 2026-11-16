# Installing the plugins

This page covers which AI coding agents (clients) can use these plugins, what each one loads, and how to install in each. Client instructions change quickly. Every client section below was checked against that client's documentation on 2026-11-16.

> [!IMPORTANT]
> Skills are instructions, not programs, but your agent acts on them: it may run commands, edit files and use the network, within the permissions your client allows. Before installing, read [Trust and safety](trust-and-safety.md) for what plugins can and can't do, how to review one, and where each client's permission controls are. To report a security problem privately, see [SECURITY.md](../SECURITY.md).

## What's portable

Each plugin follows the [Agent Plugins](https://agent-plugins.org/specification) v1.0.0 format. It has a portable `plugin.json` at the plugin root, plus client-specific files for the clients that need them. A plugin can contain four kinds of parts, and only skills work everywhere:

| Part | Format | Where it works |
| --- | --- | --- |
| Skills (`skills/<name>/SKILL.md`) | [Agent Skills](https://agentskills.io/specification) | Every client on this page |
| Agents (`agents/*.md`) | Claude Code subagent | **Claude Code only.** Copilot support is tracked in [#240](https://github.com/uw-ssec/savvy/issues/240). |
| Commands (`commands/*.md`) | Claude Code slash command | **Claude Code only.** Copilot support is tracked in [#240](https://github.com/uw-ssec/savvy/issues/240), and turning commands into portable skills in [#241](https://github.com/uw-ssec/savvy/issues/241). |
| MCP server (`mcp.json`, `.mcp.json`) | MCP configuration | Clients that install plugins load it; the rest need it added by hand. Only `holoviz-visualization` has one. |

Every plugin README carries a note saying the same thing. If a client doesn't load agents or commands, the plugin's skills still work on their own.

## Support matrix

| Client | Install from | Skills | Agents | Commands | HoloViz MCP |
| --- | --- | --- | --- | --- | --- |
| [Claude Code](#claude-code) | marketplace | ✅ | ✅ | ✅ | ✅ |
| [GitHub Copilot CLI](#github-copilot-cli) | marketplace | ✅ | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | ✅ |
| [VS Code (Copilot)](#vs-code-copilot) | marketplace setting | 🟡 | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | ❔ |
| [Codex](#codex) | marketplace | ✅ | ❌ | ❌ | ✅ |
| [Cursor](#cursor) | local folder | 🟡 | ❌ | ❌ | 🟡 |
| [Gemini CLI](#gemini-cli) | copied skills | 🟡 | ❌ | ❌ | 🔧 `settings.json` |
| [OpenCode](#opencode) | copied skills | ✅ | ❌ | ❌ | 🔧 `opencode.json` |

✅ Verified · 🟡 Expected, untested · ❔ Unknown · 🚧 Planned · ❌ Unsupported · 🔧 Manual setup

🟡 cells follow the client's documentation but haven't been run against this repository. For MCP, ✅ means the client found the server configuration; the server itself wasn't started.

Replace `scientific-python-development` in the examples below with any plugin from [Available Plugins](../README.md#available-plugins).

## Install by client

### Claude Code

```bash
claude plugin marketplace add uw-ssec/savvy
claude plugin install scientific-python-development@rse-plugins
```

Inside Claude Code, the same commands are `/plugin marketplace add uw-ssec/savvy` and `/plugin install scientific-python-development@rse-plugins`. Claude Code reads `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, and loads skills, agents, commands and MCP servers. The marketplace is named `rse-plugins`, which is why plugin names end in `@rse-plugins`.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add uw-ssec/savvy
copilot plugin install scientific-python-development@rse-plugins
```

Copilot reads the root `plugin.json` and the marketplace in `.claude-plugin/marketplace.json`, and loads each plugin's skills and MCP servers. It doesn't load our agents or commands yet: those are written for Claude Code, and Copilot-format versions for Copilot CLI and VS Code are tracked in [#240](https://github.com/uw-ssec/savvy/issues/240). The [Codespace](../README.md#github-codespaces) installs every plugin this way.

### VS Code (Copilot)

Add the repository to the `chat.plugins.marketplaces` setting in your `settings.json`:

```json
"chat.plugins.marketplaces": [
    "uw-ssec/savvy"
]
```

Then install plugins from the marketplace. See [Configure plugin marketplaces](https://code.visualstudio.com/docs/agent-customization/agent-plugins#_configure-plugin-marketplaces). Like Copilot CLI, VS Code loads skills and MCP servers but not our agents or commands ([#240](https://github.com/uw-ssec/savvy/issues/240)).

### Codex

```bash
codex plugin marketplace add uw-ssec/savvy
codex plugin add scientific-python-development@rse-plugins
```

Codex reads `.agents/plugins/marketplace.json` and loads skills and MCP servers. It doesn't load agents or commands.

### Cursor

Cursor's public marketplace is curated, so this repository isn't listed there. To use a plugin, copy it into Cursor's local plugin folder. Cursor skips symlinks that point outside that folder, so copy rather than link:

```bash
git clone https://github.com/uw-ssec/savvy.git
mkdir -p ~/.cursor/plugins/local
cp -R savvy/plugins/scientific-python-development ~/.cursor/plugins/local/
```

Then restart Cursor (or run **Developer: Reload Window**), and check the plugin's skills and MCP servers under **Customize**. Cursor loads each plugin as an Agent Plugin, which means skills and MCP servers only. Our agents and commands use Claude Code's format, so Cursor doesn't load them. Teams and Enterprise plans can also add the repository to a team marketplace (`.cursor-plugin/marketplace.json`) instead of copying. See [Cursor plugins](https://cursor.com/docs/plugins). To use skills without the plugin, copy them as in [Copy skills into any client](#copy-skills-into-any-client).

### Gemini CLI

Gemini CLI installs extensions (`gemini-extension.json`), not Agent Plugins, and this repository doesn't ship an extension. It does discover skills, so copy the skills you want into a skills directory, either in a project (`.agents/skills/`) or for your user (`~/.agents/skills/`). Gemini treats these as aliases for `.gemini/skills/` and `~/.gemini/skills/`:

```bash
git clone https://github.com/uw-ssec/savvy.git
mkdir -p .agents/skills
cp -R savvy/plugins/scientific-python-development/skills/* .agents/skills/
gemini skills list
```

In a running session, `/skills reload` picks up new skills and `/skills list` shows them. To install a single skill straight from the repository instead, `gemini skills install` takes a Git URL and a `--path` to the skill's folder. See [Agent Skills in Gemini CLI](https://geminicli.com/docs/cli/skills/).

Agents and commands aren't available, because Gemini uses its own formats for both (commands are TOML files). To use the HoloViz MCP server, add it to `~/.gemini/settings.json` (or `.gemini/settings.json` in a project) yourself:

```json
{
  "mcpServers": {
    "holoviz-mcp": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-v", "holoviz-mcp:/root/.holoviz-mcp", "ghcr.io/marcskovmadsen/holoviz-mcp:latest"]
    }
  }
}
```

These steps follow Gemini CLI's documentation; they haven't been run against this repository.

### OpenCode

OpenCode doesn't install plugin packages, but it discovers skills. Copy the skills you want into a skills directory, either globally (`~/.config/opencode/skills/` or `~/.agents/skills/`) or in a project (`.agents/skills/` or `.opencode/skills/`):

```bash
git clone https://github.com/uw-ssec/savvy.git
mkdir -p ~/.config/opencode/skills
cp -R savvy/plugins/scientific-python-development/skills/* ~/.config/opencode/skills/
```

Agents and commands aren't available in OpenCode. To use the HoloViz MCP server, add it to your `opencode.json` yourself:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "holoviz-mcp": {
      "type": "local",
      "command": ["docker", "run", "-i", "--rm", "-v", "holoviz-mcp:/root/.holoviz-mcp", "ghcr.io/marcskovmadsen/holoviz-mcp:latest"]
    }
  }
}
```

## Copy skills into any client

Every skill folder is self-contained, so you can copy it on its own into any client that reads [Agent Skills](https://agentskills.io/). `.agents/skills/` is the shared location: every client on this page except Claude Code reads it. Copy into a project to share the skills with everyone who works on it, or into your home directory to use them everywhere:

```bash
git clone https://github.com/uw-ssec/savvy.git

# For one project (run from the project root)
mkdir -p .agents/skills
cp -R savvy/plugins/scientific-python-development/skills/* .agents/skills/

# Or for your user, in every project
mkdir -p ~/.agents/skills
cp -R savvy/plugins/scientific-python-development/skills/* ~/.agents/skills/
```

Claude Code doesn't read `.agents/skills/`. Use `.claude/skills/` or `~/.claude/skills/` instead, or install the plugin, which also brings its agents and commands.

| Client | Project directory | User directory | How to check | Copy tested |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | `/skills` | 🟡 |
| GitHub Copilot CLI | `.agents/skills/` (also `.github/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.copilot/skills/`) | `copilot skill list` | ✅ `.agents/skills/`, Copilot CLI 1.0.108 |
| VS Code (Copilot) | `.agents/skills/` (also `.github/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.copilot/skills/`) | [VS Code docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills) | 🟡 |
| Codex | `.agents/skills/`, from the working directory up to the repository root | `~/.agents/skills/` | `/skills` | ✅ `.agents/skills/`, Codex CLI 0.160.0 |
| Cursor | `.agents/skills/` (also `.cursor/skills/`) | `~/.agents/skills/` (or `~/.cursor/skills/`) | **Customize** | 🟡 |
| Gemini CLI | `.agents/skills/` (or `.gemini/skills/`) | `~/.agents/skills/` (or `~/.gemini/skills/`) | `gemini skills list` | 🟡 |
| OpenCode | `.agents/skills/` (also `.opencode/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.config/opencode/skills/`) | the `skill` tool | ✅ `~/.config/opencode/skills/` |

The Copilot CLI and Codex tests (2026-11-16) put the five `scientific-python-development` skills in `.agents/skills/` of a fresh Git repository, with no plugin installed, and confirmed that the client listed all five. Codex was checked with `codex debug prompt-input`, which prints the skill list it sends to the model; an empty repository listed none of them. The OpenCode result comes from the smoke tests in [#238](https://github.com/uw-ssec/savvy/pull/238).

A copied skill doesn't update itself. To pick up fixes, pull the repository and copy again. To stay on a version you reviewed, check out a [release](https://github.com/uw-ssec/savvy/releases) tag before copying; see [Trust and safety](trust-and-safety.md).
