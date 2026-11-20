# Trust and Safety: What Plugins Can and Can't Do

This note is for researchers, and for the IT and security teams who support them, deciding whether it's safe to install a plugin from this repository. It explains what a plugin contains, what an agent can do with it, what it doesn't do, and how to review one before you install it.

To report a security problem, follow [SECURITY.md](../SECURITY.md) instead of opening a public issue.

## What's in a plugin

A plugin is a folder of text files. Installing one copies those files to where your agent client can find them, and doesn't run anything from the plugin. No plugin here ships install scripts or hooks (commands that a client runs automatically on events such as session start).

| Part | What it is |
| --- | --- |
| Skill (`skills/<name>/SKILL.md`, plus `references/`, `assets/` and sometimes `scripts/`) | Markdown instructions and reference material on one topic. The agent reads a skill when the topic comes up. |
| Agent (`agents/*.md`) | A Markdown prompt that defines a specialist persona |
| Command (`commands/*.md`) | A Markdown prompt that you start with a slash command, such as `/benchmark` |
| MCP server (`mcp.json`, `.mcp.json`) | Configuration that tells the client how to start a separate program that offers the agent extra tools. Only `holoviz-visualization` has one. |

Not every client loads every part. See the [support matrix](install.md#support-matrix) for which parts each client loads.

## Skills are instructions, not programs

A skill is guidance for the agent, written in Markdown. The client doesn't execute it. It puts the text in front of the model, much as if you'd pasted it into the chat.

Some skills also bundle Python files. Files in `assets/` are templates and examples to copy into your project. Files in `scripts/` are helpers the agent may run, such as `rechunk.py` in `zarr-chunk-optimization`. A bundled file runs only if the agent decides to run it, and then it goes through the same permission checks as any other command.

## What the agent can still do with them

Instructions shape what the agent tries to do, and the agent can act. Depending on your client and its permission settings, an agent following a skill can:

- **Run shell commands.** For example, the `pixi-package-manager` skill tells the agent how to install pixi with `curl -fsSL https://pixi.sh/install.sh | bash`, which downloads and runs the official installer.
- **Create, edit and delete files** in your project, and sometimes outside it.
- **Install packages**, which downloads code from package indexes such as PyPI and conda-forge.
- **Fetch web pages and use the network** through its own tools or through commands it runs. Several skills link to external documentation the agent may read.
- **Use your credentials.** Commands run as you, so they can use your Git, cloud and SSH credentials.

All of this happens through the agent's own tools, so your client's permission settings decide whether it happens silently, after you approve it, or not at all. A skill can't give the agent abilities your client doesn't allow, with one exception, described next.

### Tool pre-approval in Claude Code commands

In Claude Code, a command or skill can list tools in an `allowed-tools` field. Those tools then run without a permission prompt for the turn that invokes it. Many commands in this repository pre-approve `Bash`, so a command such as `/benchmark` can run shell commands without asking you first. The grant ends when you send your next message, and deny rules in your Claude Code settings still win over it.

No `SKILL.md` in this repository uses `allowed-tools` today. The [Agent Skills format](https://agentskills.io/specification) defines it as an experimental field, though, and clients that support it may pre-approve tools for a skill in the same way. Check the frontmatter of skills, commands and agents before you run them, and add deny or ask rules for anything you never want to run unprompted (see [Permission controls](#permission-controls-in-each-client)).

## What plugins don't do

- **No hidden network calls.** A skill can't contact the network on its own; text doesn't run. Network access happens only when the agent fetches a URL or runs a command, and both go through your client's permission checks.
- **No telemetry.** Nothing in this repository reports usage, prompts or data back to us or anyone else.
- **No install-time code.** Installing or updating a plugin copies files and doesn't run anything.
- **No background activity.** Plugins don't start processes or schedule tasks on their own. The one exception is the MCP server below, which your client starts.

### The HoloViz MCP server

The `holoviz-visualization` community plugin configures an MCP server. When it's enabled, your client runs `docker run ghcr.io/marcskovmadsen/holoviz-mcp:latest`, which downloads and runs a container image maintained outside this repository, then calls the tools it offers. The image uses the `latest` tag, so its contents can change without a change here. If you don't need it, disable the server in your client or remove it from the plugin's `mcp.json` and `.mcp.json` before installing.

### Bundled scripts that use the network

The `zarr-chunk-optimization` scripts (`benchmark_runner.py`, `rechunk.py` and `synthetic_data.py`) read and write cloud storage only when you give them a cloud path such as `s3://…`. They then use your local cloud credentials. With local paths they don't use the network.

## Core and Community plugins

Each plugin belongs to one of two tiers, and its directory shows which:

- **Core** (`plugins/`) plugins are written and maintained by the UW Scientific Software Engineering Center (SSEC).
- **Community** (`community-plugins/`) plugins are contributed or domain-specific. Their maintainers may be outside SSEC, and they keep the content up to date.

Maintainers review every change to a plugin in either tier against the [security review checklist](../CONTRIBUTING.md#-security-review-checklist) before merging. That review covers the exact revision being merged; a later change that adds a command or URL is reviewed again.

Review doesn't guarantee safety. A careful reviewer can still miss a problem, and the third-party tools and packages that skills point to change over time.

## Checking a skill before you install it

Skills in the trust pilot (`ai-research-workflows` for now) carry evidence you can read before you install, in the skill's own directory (`plugins/<plugin>/skills/<name>/`):

| File | What it holds |
| --- | --- |
| `skill-card.md` | What the skill does, who it's for, what credentials it needs, and its risks and mitigations. It is drafted from the skill's content and reviewed by a maintainer before merge. |
| `evals/evals.json` | Where a skill's public eval set lives. Each pilot skill has one. It holds the test cases a benchmark runs, including at least one case where the skill should not trigger. They are the input to the verdict, not evidence on their own. |
| `BENCHMARK.md` | The result of running the evals with and without the skill. It's written by the manually run [benchmark workflow](../.github/workflows/benchmark-skills.yml), then reviewed and merged by a person, so git history shows when it was run. |

Not every skill has all three yet. A missing `BENCHMARK.md` means no benchmark has been run for it.

**Reading a benchmark verdict.** A benchmark reports how the skill performed on its own eval cases. It's a measurement, not a safety guarantee, and it never blocks a release. FAIL and INCONCLUSIVE results are published as they are: a skill that failed or couldn't be measured keeps that result in `BENCHMARK.md`, sometimes with a maintainer note on why. Read a FAIL as "this skill didn't help on these cases" and INCONCLUSIVE as "too little signal to say". Check the date and model, since results change when either does. The release notes list each pilot skill's verdict.

**Capability declarations.** Each pilot skill's `SKILL.md` declares five keys under `metadata`. A value states what the skill **directs the agent to do**, not what code it ships. A maintainer reviews that the values match the skill's content; CI checks only that they are present and allowed.

| Key | Values | Meaning |
| --- | --- | --- |
| `capability-network` | `none`, `read`, `write` | `read`: tells the agent to fetch pages or packages. `write`: tells it to publish or upload. |
| `capability-shell` | `none`, `runs-commands` | `runs-commands`: tells the agent to run shell commands. |
| `capability-file` | `none`, `read`, `write` | `read`: tells the agent to read project files. `write`: tells it to create or change files. |
| `capability-environment` | `none`, `read` | `read`: tells the agent to read environment variables or credentials. |
| `capability-mcp` | `none`, `uses` | `uses`: tells the agent to call MCP tools. |

**Verifying a release archive.** Each pilot skill is attached to a [release](https://github.com/uw-ssec/savvy/releases) as a signed archive, `<plugin>--<skill>-<version>.tar.gz`, starting with the first release after the pilot lands. [`release-sign.yml`](../.github/workflows/release-sign.yml) signs it. Extract the archive, then verify the folder it creates:

```bash
tar -xzf <plugin>--<skill>-<version>.tar.gz

model_signing verify sigstore <plugin>--<skill> \
  --signature <plugin>--<skill>/skill.oms.sig \
  --identity https://github.com/uw-ssec/savvy/.github/workflows/release-sign.yml@refs/tags/<TAG> \
  --identity_provider https://token.actions.githubusercontent.com \
  --no-ignore-git-paths
```

Replace `<TAG>` with the release tag, including the leading `v` (for example `v26.12.0`). The flag spellings are mixed (`--identity_provider` has an underscore, `--no-ignore-git-paths` has hyphens) because that's how `model-signing` 1.1.1 defines them. Without `--no-ignore-git-paths`, `model_signing` skips top-level `.git*` and `.github` paths, so a `.github/` folder added to the archive wouldn't be detected.

You need the `model_signing` command. It's published on PyPI (not conda-forge, so `pixi exec` can't fetch it). With [uv](https://docs.astral.sh/uv/) installed, this runs it without a permanent install, and was tested with `--help`:

```bash
uvx --from model-signing==1.1.1 --with "pyopenssl>=26.4.0,<27" model_signing --help
```

Use the same `uvx --from … model_signing` prefix in place of `model_signing` in the verify command. `pyopenssl` is listed because `model-signing` imports it without declaring it. `pipx` or a virtual environment with `pip install model-signing==1.1.1 "pyopenssl>=26.4.0,<27"` works too. From a clone of this repository, `pixi run -e signing model_signing …` uses the pinned environment.

**What a passing verification proves.** The archive was produced by `release-sign.yml` at that tag in `uw-ssec/savvy`, and its contents haven't changed since. It doesn't prove the code at that tag was reviewed or that the skill is safe. Read the skill and its card, as described in [Before you install](#before-you-install).

## Before you install

We recommend reviewing a plugin before you install it, especially on a machine with sensitive data or credentials. A plugin is plain text, so a review takes a few minutes:

1. **Read every `SKILL.md`** in the plugin, and skim its `references/`. Look for instructions that would surprise you.
2. **Find the commands it asks for.** Search for shell code blocks and for `curl`, `wget`, `pip install`, `rm `, `sudo` and `| bash`. Decide whether you'd run each one yourself.
3. **Find the URLs.** Check that each link goes where it claims to, and that downloads come from the official source.
4. **Look for hidden text.** Instructions in HTML comments (`<!-- … -->`) don't show up when GitHub renders the file but are still passed to the agent. Read the raw files.
5. **Check tool grants.** Look at `allowed-tools` (and `tools`) in the frontmatter of skills, agents and commands.
6. **Check for MCP servers and scripts.** Look for `mcp.json`, `.mcp.json` and `scripts/` folders, and read what they start or run.

From a clone of the repository, this search lists the places to look first:

```bash
rg -n --hidden "allowed-tools|curl|wget|\| *(ba|z)?sh|sudo|rm -rf|https?://|<!--|base64" plugins/<plugin>
```

Install only the plugins you need, and install the version you reviewed rather than whatever is on `main` later:

- **Review a release, then pin it.** [Releases](https://github.com/uw-ssec/savvy/releases) are tagged, and the release notes list what changed in each plugin. In Claude Code, add `#<tag>` to pin the marketplace to a release: `claude plugin marketplace add uw-ssec/savvy#<tag>`.
- **Or copy what you reviewed.** Clone the repository, check out the tag or commit you reviewed, and copy the plugin into your client, as in [Copy skills into any client](install.md#copy-skills-into-any-client).

A pinned or copied plugin doesn't receive security fixes on its own. Watch for advisories as described in [SECURITY.md](../SECURITY.md#supported-versions), and update when one affects a plugin you use.

## Permission controls in each client

Each client decides what the agent may do without asking. Before you use a plugin with commands that change files or run code, check these settings.

| Client | Where to find permission controls |
| --- | --- |
| Claude Code | Run `/permissions` to see and edit allow, ask and deny rules, or set them in `settings.json`. Choose a permission mode (such as plan mode, which is read-only) with Shift+Tab or `defaultMode`. Deny rules always take precedence. See [Configure permissions](https://code.claude.com/docs/en/permissions). |
| GitHub Copilot CLI | Copilot asks before using a tool unless you approve it for the session. Use `/permissions` in a session, or the `--allow-tool` and `--deny-tool` flags (for example `--deny-tool='shell(rm)'`). Avoid `--allow-all-tools` and `/yolo` unless you're in a disposable environment. Trusted directories limit where Copilot reads, edits and runs files, though GitHub describes that limit as best effort. See [About GitHub Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli). |
| VS Code (Copilot) | Use the permissions picker in the chat view (Manual, Assisted, Allow all or Autopilot), the terminal auto-approval rules, and `chat.tools.edits.autoApprove`. Turn on agent sandboxing to confine shell commands, and open untrusted projects in Restricted Mode. See [Security in VS Code](https://code.visualstudio.com/docs/copilot/security). |
| Codex | Choose a sandbox mode (`read-only`, `workspace-write` or `danger-full-access`) and an approval policy with `/permissions`, the `--sandbox` and `--ask-for-approval` flags, or `~/.codex/config.toml`. By default, commands run without network access and can write only in the workspace. See [Agent approvals and security](https://developers.openai.com/codex/agent-approvals-security). |
| Antigravity CLI | Choose an agent mode with `--mode`, Shift+Tab, or **Agent Mode** in `/config`. The default mode, `auto`, approves workspace edits without asking and runs shell commands in a sandbox, and it lets commands it judges safe and reversible run outside the sandbox. `default` mode asks before every edit and command. Add `allow`, `ask` or `deny` rules (for example `command(sudo)`) with `/permissions` or in `~/.gemini/antigravity-cli/settings.json`. Deny beats ask, and ask beats allow. Avoid `--dangerously-skip-permissions` unless you're in a disposable environment. See [Permissions](https://antigravity.google/docs/permissions) and [Modes](https://antigravity.google/docs/cli/modes). |
| Cursor | **Settings → Agents → Approvals & Execution** sets the run mode (Auto-review, Allowlist or Run Everything), the command and MCP allowlists, and file-deletion and external-file protection. `sandbox.json` limits what sandboxed commands can reach on disk and on the network. See [Run modes](https://cursor.com/docs/agent/run-modes) and [Agent security](https://cursor.com/docs/agent/security). |
| OpenCode | Add permission rules (`allow`, `ask` or `deny` per action, such as `shell`, `edit` and `webfetch`) to `opencode.json`. OpenCode allows most actions without asking by default, so add an `ask` rule for `shell` if you want to approve commands. See [Permissions](https://opencode.ai/docs/permissions/). |

These links point to each client's own documentation, which changes faster than this note. If a setting has moved, the linked page is the source of truth.

## Questions

For general questions about this note, [open an issue](https://github.com/uw-ssec/savvy/issues). For anything that might be a vulnerability, use [SECURITY.md](../SECURITY.md).
