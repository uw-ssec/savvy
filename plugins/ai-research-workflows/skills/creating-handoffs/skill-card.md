# Skill Card: creating-handoffs

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to write a handoff document that carries the current working context (tasks, phase, critical files, learnings, research state, verification status, next steps) to a later session or person. It is a set of written instructions, one reference (`references/writing-guide.md`) and one template (`assets/handoff-template.md`); it ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who use a coding agent and need to pause work and resume it in a fresh session. Typical triggers: "create a handoff", "hand off this work", "summarize context for the next session". The skill recommends which workflow skill the next session should invoke.

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`, so it does not direct the agent to read environment variables or secrets.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access.
- `capability-shell: runs-commands`. The skill directs the agent to run `git branch --show-current`, `git rev-parse --short HEAD`, `git status` and `git diff --stat`, which are read-only git queries, and to re-run the project's test suite so the handoff reports the observed status. The reference suggests scheduler status queries (`squeue -j <id>`, `sacct -j <id>`) for the handoff to record. The agent runs these with the user's permissions, and the test suite runs the project's own code. The skill tells the agent to leave the working tree as it found it: not to commit, stash or revert work.
- `capability-file: write`. The skill directs the agent to write `docs/rse/specs/handoff-YYYY-MM-DD-HH-MM-<slug>.md` and to read existing workflow documents in `docs/rse/specs/` (and legacy `.agents/`).
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: the handoff is built from the conversation and working tree, so it can leave out or misstate the true state of the work (failing tests, uncommitted changes).
Mitigation: the skill requires the agent to re-run the tests and to surface uncommitted or unpushed work, failing or unrun tests and unverified results in a "Known-broken / unverified" callout. A person should still read the handoff before relying on it.

Risk: the handoff is a file in a repository path (`docs/rse/specs/`) that the surrounding workflow treats as committed and version-controlled. Conversation content the agent copies into it, including anything sensitive that appeared in the session, can end up in version control. The skill does not instruct the agent to filter secrets.
Mitigation: review the handoff before committing it.

Risk: the handoff is an instruction carrier. The next session is told to "Read the handoff document ... and resume the work described within", and the skill feeds earlier handoffs and legacy `.agents/` files into the new one, so stale, mistaken or planted content in those files propagates into a session that acts on it.
Mitigation: none in the skill. A person should read the handoff, and any earlier handoff it draws on, before the next session is told to act on it.

## Output

**Output Type(s):** Files (Markdown), plus a short summary presented in the conversation.
**Output Format:** Markdown following `assets/handoff-template.md`, saved as `docs/rse/specs/handoff-YYYY-MM-DD-HH-MM-<slug>.md`.
**Other Properties:** names the 2-3 files the next session should read first and the recommended next skill.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--creating-handoffs-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

The handoff is a record other people may rely on, so it must be honest: the skill says a clean-looking handoff that hides broken or unverified state is worse than none. Do not use a handoff to pass on private conversation content or credentials. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/writing-guide.md](references/writing-guide.md)
- [assets/handoff-template.md](assets/handoff-template.md)
