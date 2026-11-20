# Installing the plugins

This page covers which AI coding agents (clients) can use these plugins, what each one loads, and how to install in each. Client instructions change quickly. Every client section below was checked against that client's documentation on 2026-11-16, except Antigravity CLI, which was checked on 2026-11-20.

> [!IMPORTANT]
> Skills are instructions, not programs, but your agent acts on them: it may run commands, edit files and use the network, within the permissions your client allows. Before installing, read [Trust and safety](trust-and-safety.md) for what plugins can and can't do, how to review one, and where each client's permission controls are. To report a security problem privately, see [SECURITY.md](../SECURITY.md).

## What's portable

Each plugin follows the [Agent Plugins](https://agent-plugins.org/specification) v1.0.0 format. It has a portable `plugin.json` at the plugin root, plus client-specific files for the clients that need them. A plugin can contain four kinds of parts, and only skills work everywhere:

| Part | Format | Where it works |
| --- | --- | --- |
| Skills (`skills/<name>/SKILL.md`) | [Agent Skills](https://agentskills.io/specification) | Every client on this page |
| Agents (`agents/*.md`) | Claude Code subagent | **Claude Code, Cursor and Antigravity CLI.** Copilot support is tracked in [#240](https://github.com/uw-ssec/savvy/issues/240). |
| Commands (`commands/*.md`) | Claude Code slash command | **Claude Code and Cursor.** Copilot support is tracked in [#240](https://github.com/uw-ssec/savvy/issues/240), and turning commands into portable skills in [#241](https://github.com/uw-ssec/savvy/issues/241). |
| MCP server (`mcp.json`, `.mcp.json`) | MCP configuration | Clients that install plugins load it, except Antigravity CLI ([#305](https://github.com/uw-ssec/savvy/issues/305)); the rest need it added by hand. Only `holoviz-visualization` has one. |

Every plugin README carries a note saying the same thing. If a client doesn't load agents or commands, the plugin's skills still work on their own.

## Support matrix

| Client | Install from | Skills | Agents | Commands | HoloViz MCP |
| --- | --- | --- | --- | --- | --- |
| [Claude Code](#claude-code) | marketplace | ✅ | ✅ | ✅ | ✅ |
| [GitHub Copilot CLI](#github-copilot-cli) | marketplace | ✅ | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | ✅ |
| [VS Code (Copilot)](#vs-code-copilot) | marketplace setting | 🟡 | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | 🚧 [#240](https://github.com/uw-ssec/savvy/issues/240) | ❔ |
| [Codex](#codex) | marketplace | ✅ | ❌ | ❌ | ✅ |
| [Cursor](#cursor) | local folder | ✅ | ✅ | ✅ | ✅ |
| [Antigravity CLI](#antigravity-cli) | GitHub folder | ✅ | ✅ | ❌ | 🔧 `agy mcp add` |
| [OpenCode](#opencode) | copied skills | ✅ | ❌ | ❌ | 🔧 `opencode.json` |

✅ Verified · 🟡 Expected, untested · ❔ Unknown · 🚧 Planned · ❌ Unsupported · 🔧 Manual setup

🟡 cells follow the client's documentation but haven't been run against this repository. For MCP, ✅ means the client found the server configuration; the server itself wasn't started.

Replace `scientific-python-development` in the examples below with any plugin from the [skill catalog](catalog.md).

## Install by client

### Claude Code

```bash
claude plugin marketplace add uw-ssec/savvy
claude plugin install scientific-python-development@savvy
```

Inside Claude Code, the same commands are `/plugin marketplace add uw-ssec/savvy` and `/plugin install scientific-python-development@savvy`. Claude Code reads `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, and loads skills, agents, commands and MCP servers. The marketplace is named `savvy`, which is why plugin names end in `@savvy`.

### GitHub Copilot CLI

```bash
copilot plugin marketplace add uw-ssec/savvy
copilot plugin install scientific-python-development@savvy
```

Copilot reads the root `plugin.json` and the marketplace in `.claude-plugin/marketplace.json`, and loads each plugin's skills and MCP servers. It doesn't load our agents or commands yet: those are written for Claude Code, and Copilot-format versions for Copilot CLI and VS Code are tracked in [#240](https://github.com/uw-ssec/savvy/issues/240). The [Codespace](codespaces.md) installs every plugin this way.

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
codex plugin add scientific-python-development@savvy
```

Codex reads `.agents/plugins/marketplace.json` and loads skills and MCP servers. It doesn't load agents or commands.

### Cursor

Cursor's public marketplace is curated, so this repository isn't listed there. To use a plugin, copy it into Cursor's local plugin folder. Cursor skips symlinks that point outside that folder, so copy rather than link:

```bash
git clone https://github.com/uw-ssec/savvy.git
mkdir -p ~/.cursor/plugins/local
cp -R savvy/plugins/scientific-python-development ~/.cursor/plugins/local/
```

Cursor picks up the new folder on its own. If the plugin doesn't appear under **Customize**, restart Cursor or run **Developer: Reload Window**. Cursor documents a plugin with a root `plugin.json` as skills and MCP servers only, but it also loads our agents as subagents and our commands in the `/` menu. Teams and Enterprise plans can also add the repository to a team marketplace (`.cursor-plugin/marketplace.json`) instead of copying. See [Cursor plugins](https://cursor.com/docs/plugins). Tested with Cursor 3.28.7; the team marketplace hasn't been tested. To use skills without the plugin, copy them as in [Copy skills into any client](#copy-skills-into-any-client).

### Antigravity CLI

```bash
agy plugin install https://github.com/uw-ssec/savvy/tree/main/plugins/scientific-python-development
agy plugin list
```

Antigravity's plugin marketplace lists only Google's official catalog, so install a plugin from its folder on GitHub, as above, or from a local clone (`agy plugin install ./savvy/plugins/scientific-python-development`). Plugins are installed for your user, in `~/.gemini/config/plugins/`. To see what a plugin will load before you install it, run `agy plugin validate` on its folder.

Antigravity loads the plugin's skills and agents; `agy agents` lists the agents. It skips agents that set `model: sonnet`, which leaves out nine of the ten `uiux-design-team` agents ([#306](https://github.com/uw-ssec/savvy/issues/306)). It doesn't load commands. The install summary says they were converted to skills, but they don't show up in a session, and where a command shares its name with a skill, you get the skill.

Antigravity reads a plugin's MCP servers from `mcp_config.json`, which our plugins don't ship yet ([#305](https://github.com/uw-ssec/savvy/issues/305)). To use the HoloViz MCP server, add it yourself:

```bash
agy mcp add holoviz-mcp -- docker run -i --rm -v holoviz-mcp:/root/.holoviz-mcp ghcr.io/marcskovmadsen/holoviz-mcp:latest
```

This writes the server to `~/.gemini/config/mcp_config.json`. For a single project, put the same `mcpServers` entry in `.agents/mcp_config.json`. See [Plugins](https://antigravity.google/docs/plugins?tab=cli) and [MCP](https://antigravity.google/docs/mcp?tab=cli). Tested with Antigravity CLI 1.5.13: `scientific-python-development`, `ai-research-workflows`, `holoviz-visualization` and `uiux-design-team` were installed from local folders, and `scientific-python-development` also from its GitHub URL.

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

Claude Code doesn't read `.agents/skills/`. Use `.claude/skills/` or `~/.claude/skills/` instead, or install the plugin, which also brings its agents and commands. Antigravity CLI reads `.agents/skills/` in a project but not `~/.agents/skills/`. For your user, copy into `~/.gemini/config/skills/` instead.

| Client | Project directory | User directory | How to check | Copy tested |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | `/skills` | 🟡 |
| GitHub Copilot CLI | `.agents/skills/` (also `.github/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.copilot/skills/`) | `copilot skill list` | ✅ `.agents/skills/`, Copilot CLI 1.0.108 |
| VS Code (Copilot) | `.agents/skills/` (also `.github/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.copilot/skills/`) | [VS Code docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills) | 🟡 |
| Codex | `.agents/skills/`, from the working directory up to the repository root | `~/.agents/skills/` | `/skills` | ✅ `.agents/skills/`, Codex CLI 0.160.0 |
| Cursor | `.agents/skills/` (also `.cursor/skills/`) | `~/.agents/skills/` (or `~/.cursor/skills/`) | **Customize** | 🟡 |
| Antigravity CLI | `.agents/skills/`, from the working directory up to the repository root | `~/.gemini/config/skills/` (not `~/.agents/skills/`) | ask the agent, after `/skills reload` | ✅ `.agents/skills/` and `~/.gemini/config/skills/`, Antigravity CLI 1.5.13 |
| OpenCode | `.agents/skills/` (also `.opencode/skills/`, `.claude/skills/`) | `~/.agents/skills/` (or `~/.config/opencode/skills/`) | the `skill` tool | ✅ `~/.config/opencode/skills/` |

The Copilot CLI and Codex tests (2026-11-16) put the five `scientific-python-development` skills in `.agents/skills/` of a fresh Git repository, with no plugin installed, and confirmed that the client listed all five. Codex was checked with `codex debug prompt-input`, which prints the skill list it sends to the model; an empty repository listed none of them. The Antigravity CLI test (2026-11-20) did the same, in `.agents/skills/` and then in `~/.gemini/config/skills/`, using `agy -p` to ask the agent for its skill list. Skills that were already in `~/.agents/skills/` on that machine weren't listed. The OpenCode result comes from the smoke tests in [#238](https://github.com/uw-ssec/savvy/pull/238).

A copied skill doesn't update itself. To pick up fixes, pull the repository and copy again. To stay on a version you reviewed, check out a [release](https://github.com/uw-ssec/savvy/releases) tag before copying; see [Trust and safety](trust-and-safety.md).
