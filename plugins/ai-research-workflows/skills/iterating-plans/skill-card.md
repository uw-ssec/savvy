# Skill Card: iterating-plans

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to revise an existing implementation plan (`docs/rse/specs/plan-*.md`) with focused edits: read the whole plan, research the codebase if the change needs it, propose the changes (and, in the default Collaborative mode, get the user's confirmation), edit surgically, and run a required consistency scan. It is written instructions plus a reference document and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who need to change a plan before or during execution: add a phase, revise scope, update success criteria, or fold in experiment results. Typical triggers: "update the plan", "add a phase", "split a phase", "revise scope", "incorporate experiment results".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access.
- `capability-shell: runs-commands`. The skill directs the agent to list recent plans (`ls -lt docs/rse/specs/plan-*.md ...`) and, when a change needs it, to investigate the codebase (searching and reading files). The agent runs these commands with the user's permissions.
- `capability-file: write`. The skill directs the agent to edit the existing plan file in place.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: edits to a plan can break its internal consistency (phase numbering, cross-references, the automated versus manual verification split) or silently invalidate its reproducibility or numerical-correctness criteria.
Mitigation: the skill requires a numbered consistency scan after every edit (contiguous phase numbers, resolving cross-references, no references to removed work, the Automated/Manual split intact, no open questions) and a re-check of the research criteria when the approach changes or a results-producing phase is added. Confirmation is keyed to the interaction mode: in Collaborative mode (the default, including a bare "go" or a specific change request) the agent presents the proposed changes and does not write to the plan file until the user says yes; only when the user says not to check back ("no need to check back", "don't ask", "just do it") does the agent state the intended edits and then apply them.

Risk: an agent rewrites more of the plan than was asked.
Mitigation: the skill specifies surgical edits and lists whole-plan rewrites as a bad edit. Review the diff of the plan.

## Output

**Output Type(s):** Files (an edited plan).
**Output Format:** Markdown edits in place to `docs/rse/specs/plan-<slug>.md`, plus a short change summary in the conversation.
**Other Properties:** `file:line` references for any new task.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--iterating-plans-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

The plan may later be executed by an agent with the user's permissions, so an altered plan changes what the agent will do. The skill therefore states every intended edit before it is written, asks the user to confirm unless the user has said not to check back, and raises conflicts rather than hiding them. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/iteration-patterns.md](references/iteration-patterns.md)
