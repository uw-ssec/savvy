# Skill Card: using-research-workflows

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

A routing skill for the `ai-research-workflows` plugin. It tells the agent to pick and invoke the matching workflow skill (researching, planning, iterating on plans, experimenting, implementing, validating, reproducing, hardening, handing off) before acting on a research-software task, and explains the Collaborative and Direct interaction modes and the document naming scheme. It is written instructions plus one reference document and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers starting or continuing any research-software task who want the agent to follow the plugin's structured workflow. Typical triggers: "which skill should I use", "where do I start", "guide me through the workflow".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access.
- `capability-shell: none`. The skill does not direct the agent to run commands. It routes to other skills, which carry their own capabilities and cards.
- `capability-file: write`. The skill describes where workflow documents are written (`docs/rse/specs/`) and tells the agent to search that location and the legacy `.agents/` location when reading. It does not itself produce a document.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: the skill is written in strongly directive language. It says that if there is a 1% chance a workflow skill applies the agent must invoke it, and it ranks itself above the client's default system prompt (below the user's explicit instructions). This can make an agent run more skills, and more steps, than a small task needs.
Mitigation: the skill ranks the user's explicit instructions highest, and a clear "Don't plan, just write it" wins. That is narrow: a directive such as "fix the loader", "just add X" or "don't overthink it" states what to do and does not authorize skipping the workflow, and "just do it" selects Direct mode rather than disabling it. The aim is the minimal matching skill, not the whole chain. The skill also ranks itself above the client's default system prompt, and nothing in it mitigates that; operator or system-prompt policy that conflicts with it is declared lower priority. Users who do not want the compulsion or that precedence should not install this skill.

Risk: because it routes to other skills, what actually runs depends on those skills.
Mitigation: the nine sibling skills in this plugin each have their own capability declarations and skill card; review those too. The deferral targets outside this plugin (the `scientific-python-development` skills, `project-management:community-health-files`, the `/project-handoff` command and an external `deep-research` skill) have no skill card or capability declarations in this pilot, so review them separately.

## Output

**Output Type(s):** None directly (routing guidance in the agent's behavior).
**Output Format:** not applicable. Other skills write the `research-`, `plan-`, `experiment-`, `implement-`, `validation-` and `handoff-` documents in `docs/rse/specs/`.
**Other Properties:** none.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--using-research-workflows-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

The skill directs the agent, in strongly directive language, toward understanding code before changing it, verifying before reporting, and capturing provenance for results that will be relied on. It deliberately constrains agent behavior, so teams should decide whether that suits their working style. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/interaction-modes.md](references/interaction-modes.md)
