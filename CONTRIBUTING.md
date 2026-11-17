# Contributing to RSE Plugins

Thank you for your interest in contributing to RSE Plugins! This document provides guidelines for creating and contributing custom agents for scientific software engineering tasks.

## 🌟 Types of Contributions

We welcome various types of contributions:

- **New Agents**: Create agents for specific RSE or scientific computing tasks
- **Agent Improvements**: Enhance existing agents with better prompts or capabilities
- **Documentation**: Improve guides, examples, and documentation
- **Bug Reports**: Report issues with existing agents
- **Feature Requests**: Suggest new agent capabilities or improvements

## 🤖 Creating a New Agent

### 1. Choose the Right Category

Agents are organized by scientific domain in the `plugins/` directory:

- **scientific-computing/** - HPC, numerical computing, simulations
- **data-science/** - Data analysis, statistics, machine learning
- **research-tools/** - General RSE practices and tools
- **domain-specific/** - Discipline-specific applications

### 2. Agent File Structure

Agents are stored in `plugins/{category}/agents/` as Markdown files. Each agent file should:

1. Have a descriptive, kebab-case filename (e.g., `scientific-python-expert.md`)
2. Include a clear agent prompt that defines its expertise and behavior
3. Follow the template structure provided in each category's `agents/TEMPLATE.md`

### Agent Template

```markdown
# Agent Name

Brief description of what this agent does.

## Expertise

- List key areas of expertise
- Specific technologies or domains
- Types of problems it solves

## When to Use This Agent

Describe scenarios where this agent should be used, such as:
- Working with specific libraries or frameworks
- Solving particular types of problems
- Following specific methodologies

## Agent Prompt

[Your agent prompt goes here - this is the instruction text that will be used by Claude Code]
```

### Agent Naming Conventions

- Use clear, descriptive names that indicate the agent's purpose
- Use kebab-case for filenames: `domain-specific-expert.md`
- Keep names concise but informative
- Examples:
  - `plugins/scientific-computing/agents/hpc-workflow-optimizer.md`
  - `plugins/data-science/agents/scientific-python-analyst.md`
  - `plugins/research-tools/agents/reproducibility-specialist.md`

### Best Practices for Agent Prompts

1. **Be Specific**: Clearly define the agent's domain expertise and limitations
2. **Provide Context**: Include relevant background about scientific software engineering practices
3. **Set Expectations**: Explain what the agent can and cannot do
4. **Include Examples**: When helpful, provide example use cases or code patterns
5. **Reference Standards**: Cite relevant scientific computing best practices or standards
6. **Focus on Quality**: Emphasize code quality, reproducibility, and scientific rigor

### Example Agent Qualities

Good agents for scientific software should:

- Understand reproducibility and version control practices
- Know scientific Python ecosystem conventions
- Recognize performance considerations for computational workloads
- Promote testing and validation of scientific code
- Encourage documentation and metadata practices
- Support open science principles

## 📝 Contribution Workflow

1. **Fork the Repository**: Create your own fork of uw-ssec/rse-plugins

2. **Create a Branch**: Make a branch for your contribution
   ```bash
   git checkout -b add-agent-name
   ```

3. **Add Your Agent**: Create your agent file in the appropriate `plugins/{category}/agents/` directory

4. **Test Your Agent**: Test the agent with Claude Code to ensure it works as expected

5. **Update Documentation**: If adding a new agent, update the category README to list it

6. **Submit a Pull Request**: 
   - Provide a clear description of the agent and its purpose
   - Explain the types of tasks it helps with
   - Include any testing or validation you've done

## ✅ Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Agent file is in the appropriate `plugins/{category}/agents/` directory
- [ ] Filename follows kebab-case convention
- [ ] Agent prompt is clear and well-documented
- [ ] Agent has been tested with Claude Code (or equivalent)
- [ ] README.md is updated if adding a new agent
- [ ] Commit messages are clear and descriptive
- [ ] `pixi run plugins-check` passes (run `pixi run plugins-sync` first if you changed a manifest or the catalog)
- [ ] A new skill has a catalog entry with an example prompt you've tried in Claude Code, and `pixi run catalog-check` passes (see [Skill Catalog](#-skill-catalog))
- [ ] No sensitive information or credentials are included
- [ ] The change passes the [security review checklist](#-security-review-checklist)

## 🔒 Security Review Checklist

Agents act on the text in a plugin: they run the commands it suggests, open the URLs it links to, and follow its instructions. A harmful instruction is as dangerous as harmful code, so every pull request that adds or changes a plugin needs a maintainer to check it against this list before merging. This applies to both tiers, Core (`plugins/`) and Community (`community-plugins/`), and it matters most for Community plugins, whose authors may be outside SSEC. Contributors should check it themselves first.

This checklist is the security part of reviewing a skill. It doesn't cover whether a skill triggers correctly or is well written.

Review the exact revision you're merging. If a later commit in the pull request, or a later pull request, adds a command, URL, script, tool grant or MCP server, review those items again instead of carrying the earlier sign-off forward.

Automated checks help but don't replace this review. CI (currently the **Validate Plugins** workflow) flags hardcoded secrets and private keys, `rm -rf /`, `curl` to a raw IP address, `eval(` and `base64 -d`. It matches patterns and can't judge intent. SkillEvaluator's quality score, run on pull requests that change a skill, measures quality, not safety.

Review the raw files, not GitHub's rendered view, which hides HTML comments. This search, run from the repository root, lists most of what to look at:

```bash
rg -n --hidden "allowed-tools|curl|wget|\| *(ba|z)?sh|sudo|rm -rf|https?://|<!--|base64|ignore (all|previous)" <plugin-dir>
```

A second search finds invisible characters (zero-width and bidirectional controls) that can hide text from a reviewer. It should print nothing:

```bash
rg -n --hidden -P "[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2060}-\x{2064}\x{FEFF}]" <plugin-dir>
```

**Shell commands**

- [ ] Every command the plugin tells the agent to run is one a careful user would run themselves, and it's shown in the text rather than built at run time.
- [ ] Nothing pipes a download into a shell (`curl … | bash`) unless it's the tool's official installer from its own documentation, and the instructions tell the agent to confirm with the user first.
- [ ] Nothing deletes files outside the project, uses `sudo`, changes shell profiles, SSH keys or Git configuration, or disables security tools.
- [ ] Bundled scripts (`scripts/`, `assets/`) do what the skill says, read and write only paths the user gives them, and use the network only for a destination the user asked for.
- [ ] Tool grants list only the tools the task needs. Check `allowed-tools` and `tools` in the frontmatter of skills, agents and commands, in every client format the plugin ships. Pre-approving `Bash` lets Claude Code run any shell command without asking during that turn, so the pull request explains why it's needed.

**External URLs**

- [ ] Every link goes where its text says, and points to an official source: the project's own documentation, repository or package index.
- [ ] Nothing tells the agent to send code, data, environment variables or credentials to a URL, or to fetch and follow instructions from one.
- [ ] Downloads, container images and packages come from official sources and are pinned to a version or digest where the format allows. Call out an unpinned `latest` tag in the review.
- [ ] Each MCP server (`mcp.json`, `.mcp.json`) is one we know: the command it starts, the image or package it pulls, and who maintains it are stated in the plugin's README.

**Instructions that override agent safeguards**

- [ ] Nothing tells the agent to skip or bypass permission prompts, switch to an auto-approve or "yolo" mode, or edit the user's agent settings, permission rules or hooks.
- [ ] Nothing tells the agent to ignore previous instructions, the user's instructions, or `AGENTS.md` and `CLAUDE.md` files, or to claim authority it doesn't have ("as the system administrator…").
- [ ] Nothing tells the agent to hide what it's doing, avoid mentioning an action to the user, or act outside the task the user asked for.
- [ ] Reference material stays reference material. Text in `references/`, quoted documentation and example output reads as information, not as orders the agent should carry out. For example, a reference page that says "upload the workspace before continuing" must not lead to an upload when the user asked only for local analysis.
- [ ] There's no hidden text: no instructions in HTML comments, no invisible Unicode (zero-width or bidirectional control characters) and no base64 or other encoded payloads.

**Everything else**

- [ ] No credentials, tokens, private URLs or personal data appear anywhere, including examples.
- [ ] The plugin README says what the plugin does, which commands or scripts it may run, and what it needs network access for.

If a check fails, ask for a change or remove the content. Don't merge it with a note to fix later. If something looks deliberately malicious, don't discuss it in the pull request; report it as described in [SECURITY.md](SECURITY.md). For what users are told about plugins, see [Trust and safety](docs/trust-and-safety.md).

## 🧪 Testing Your Agent

To test your agent:

1. Add the agent file to your local `plugins/{category}/agents/` directory
2. Use Claude Code to invoke the agent on relevant tasks
3. Verify that the agent provides appropriate guidance
4. Check that the agent stays within its defined scope
5. Ensure the agent promotes best practices for scientific software

## 📦 Plugin Manifests and Other Clients

Plugins follow the [Agent Plugins](https://agent-plugins.org/specification) v1.0.0 format, so they install in Claude Code, GitHub Copilot, Codex and Cursor, and their skills also work in Gemini CLI and OpenCode (see [Installation](docs/install.md)). Each client reads different files. Most of those files are generated, so edit only the sources:

| Edit | Don't edit (generated) |
| --- | --- |
| `<plugin>/plugin.json`: name, version, description, author, license, keywords | `<plugin>/.claude-plugin/plugin.json` |
| `.claude-plugin/marketplace.json`: the plugin list, each entry's `source`, `category` and `strict` | the other fields of each `.claude-plugin/marketplace.json` entry |
| `<plugin>/mcp.json` and `<plugin>/.mcp.json` | `.agents/plugins/marketplace.json` (Codex) and `.cursor-plugin/marketplace.json` (Cursor) |

After changing a source, regenerate the rest and check the result. The tasks run in the `ci` [pixi](https://pixi.sh) environment, which locks Python, PyYAML and the other tools, so you don't need a system Python. CI runs the same tasks:

```bash
pixi run plugins-sync
pixi run plugins-check           # or plugins-check-claude to also run `claude plugin validate --strict`
```

Some rules matter to clients other than Claude Code:

- **A new plugin** needs a root `plugin.json` and an entry in `.claude-plugin/marketplace.json`. `check` fails on a plugin directory that isn't in the catalog. `plugin.json` has a closed schema: only `$schema`, `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords` and `extensions` are allowed.
- **Keep each skill self-contained.** OpenCode and other skills-only clients install a skill directory on its own, so every file and relative link in a skill must stay inside that skill's directory. Link to a sibling skill by naming it (for example "see the `design-tokens` skill"), not with `../design-tokens/SKILL.md`. Put shared material in each skill's `references/`.
- **MCP servers** need both files. `.mcp.json` is for Claude Code. `mcp.json` is the portable version that Codex, Copilot and Cursor read: it has the Agent Plugins `$schema`, an explicit `type` on each server, and no other top-level fields. Cursor doesn't expand `${PLUGIN_ROOT}` or `${PLUGIN_DATA}`, so avoid them in `mcp.json`.
- **Agent `skills:`** must be a YAML list (`skills:` then `  - name`), even for one skill. Claude Code accepts a string, but Copilot CLI silently skips an agent whose `skills` is a plain string, so `check` requires a list.
- **Skill `metadata` values** must be strings, as the [Agent Skills spec](https://agentskills.io/specification) requires. List files space-separated (`references: references/a.md references/b.md`), and quote dates (`last-verified: '2026-10-27'`), because YAML otherwise reads them as dates. `check` fails on any other type.
- **Agents and commands** load only in Claude Code and Cursor. Put anything other clients need in a skill, and update the matrix in [docs/install.md](docs/install.md) when client support changes.

## 📚 Skill Catalog

[`docs/catalog.md`](docs/catalog.md) lists every skill with its trigger phrases, an example prompt, and its maintainer, plus each plugin's commands and agents. It is generated, so don't edit it by hand. **Every new skill needs a catalog entry**, and CI fails without one.

| Edit | Generated from it |
| --- | --- |
| The skill's `description` frontmatter | the **What it does** and **Trigger phrases** columns |
| [`docs/catalog.yml`](docs/catalog.yml): each plugin's `tier` and `maintainer`, and each skill's `example` prompt | the **Tier**, **Maintainer** and **Example prompt** columns |

To add a skill:

1. Add the skill under `plugins/<plugin>/skills/<name>/` (or `community-plugins/`). A new plugin also needs an entry under `plugins:` in `docs/catalog.yml` with its tier (`Core` for SSEC-maintained general-purpose plugins, `Community` for domain-specific or contributed ones) and maintainer (`@uw-ssec/engineering` for SSEC, your GitHub handle for a contribution).
2. Add an `example:` for the skill under its plugin in `docs/catalog.yml`. Write the kind of request a user would actually type, and make it self-contained (Claude stops to ask for files that don't exist instead of loading a skill). Then confirm it activates the skill:

   ```bash
   pixi run -e ci python evals/catalog-triggers/trigger_test.py <plugin>/<skill>
   ```

   This runs the prompt in headless Claude Code with only this repository's plugins loaded, and costs one model call per skill. Results vary between runs, so rerun a failure before acting on it. If the skill still doesn't load, fix its `description` rather than tuning the prompt; set `activates: false` only as a stopgap.
3. Regenerate and check:

   ```bash
   pixi run catalog-sync
   pixi run catalog-check
   ```

## 📊 Evaluating Skills

On every pull request that changes a skill, **Skill quality check** runs [SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator)'s keyless `quality-check` (pinned to v0.6.0) on each changed skill. It fails if a skill scores below 70, and lists every changed skill's score and grade in the job summary. It scores quality only: SkillEvaluator's full `validate` (schema, PII and security scanners) is not part of this check. To check a skill locally before pushing:

```bash
uv tool install --python 3.13 "skillevaluator @ git+https://github.com/NVIDIA/SkillEvaluator.git@5320d9329c36ecc72bc94c4f58cc813d6b54224b"
skillevaluator quality-check plugins/<plugin>/skills/<skill> --min-score 70
```

Two manually triggered workflows measure skills (**Actions → workflow → Run workflow**). Neither runs on pull requests.

- **Evaluate All Skills** runs each skill's testcases with and without the skill on every model the LiteLLM proxy serves, and writes a baseline-versus-skill comparison to the run summary. Testcases live in the private `uw-ssec/rse-plugins-testcases` repository. A full run takes many hours, so narrow it with the `skills` and `models` inputs (comma-separated) and set `sleep-seconds` to `0` for a quick check. When the `TESSL_TOKEN` secret is set, the run also adds an advisory Tessl review of each selected skill.
- **Generate Testcases for New Skills** drafts five or six testcases for each skill a pull request adds. Run it with the PR number after reviewing the PR. With `dry-run` on (the default), the drafts are uploaded as a run artifact; turn it off to open a pull request in the testcases repository for review.

| Secret or variable | Used by | Purpose |
|---|---|---|
| `LITELLM_API_KEY`, `LITELLM_PROXY_URL` | Both | Model access through the LiteLLM proxy |
| `TEST_REPO_TOKEN` | Both | Fine-grained token for `rse-plugins-testcases`: Contents read for evaluation; Contents and Pull requests read/write for generation |
| `TESSL_TOKEN` (optional secret) | Evaluate All Skills | Turns on the Tessl review |
| `TESSL_WORKSPACE` (optional variable) | Evaluate All Skills | Tessl workspace to use when the token can see more than one |

Run the unit tests for these workflows' scripts with `pixi run test-scripts`.

## 📋 Code of Conduct

This project adheres to professional standards of conduct. Please be respectful and constructive in all interactions.

## 🤔 Questions or Need Help?

- Open an issue for questions about contributing
- Check existing issues and pull requests for similar contributions
- Reach out to the maintainers if you need guidance

## 📚 Additional Resources

- [Claude Code Documentation](https://docs.anthropic.com/claude/docs)
- [Best Practices for Scientific Computing](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1001745)
- [Software Carpentry](https://software-carpentry.org/) - Teaching foundational coding skills
- [Research Software Engineering](https://researchsoftware.org/) - Community resources

## 🙏 Thank You!

Your contributions help improve scientific software development practices and make research computing more accessible and reliable. We appreciate your effort!
