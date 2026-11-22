# Skill Card: planning-implementations

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to produce a phased implementation plan grounded in the actual codebase, with `file:line` references, test-first tasks, split automated and manual success criteria, explicit scope boundaries and no open questions (each decision is recorded under Resolved Decisions). It is written instructions, a plan-writing reference (`references/plan-writing.md`) and a plan template (`assets/plan-template.md`), and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who need a feature, refactor or multi-file change designed before any code is written. Typical triggers: "plan X", "design the implementation", "how should we build X", "create an implementation plan". Revising an existing plan belongs to `iterating-plans`. The resulting plan is the input to `implementing-plans`.

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access.
- `capability-shell: none`. The skill does not direct the agent to run commands. It directs the agent to read files and research documents.
- `capability-file: write`. The skill directs the agent to write `docs/rse/specs/plan-<slug>.md` (creating `docs/rse/specs/` if needed) and to read project files and existing research and experiment documents.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: the plan contains commands and verification steps that a later agent run (the `implementing-plans` skill) will execute with the user's permissions. A flawed or unsafe plan therefore has downstream effects even though this skill runs nothing.
Mitigation: the skill requires the exact command or code for each step rather than a paraphrase, and in Collaborative mode requires user sign-off on the approach and phasing. A person should read the plan before it is executed.

Risk: a plan that sounds complete but rests on a wrong reading of the code.
Mitigation: the skill requires every phase to carry `file:line` references from files the agent has read completely, forbids placeholders such as "TBD" or "add appropriate error handling", and forbids shipping unresolved questions, including when the user asks to leave a decision open: the agent offers options with a recommendation and asks the user to choose.

## Output

**Output Type(s):** Files (Markdown).
**Output Format:** `docs/rse/specs/plan-<slug>.md` following `assets/plan-template.md`, with relative links to the research and experiment documents it uses.
**Other Properties:** success criteria split into Automated and Manual verification.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--planning-implementations-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

A plan records decisions that affect later work, so in Collaborative mode (the default lean) the skill asks that design options and trade-offs be shown to the user, and in Direct mode (used only when the user asks for it or can't be consulted) nothing is required to be shown before the plan is written, but the decisions the agent made are recorded in the plan's Resolved Decisions section. It also asks that scope boundaries ("What We're NOT Doing") be stated, rather than decided silently. For numerical research code, it points to `hardening-research-code` so that planned tests check against known results. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/plan-writing.md](references/plan-writing.md)
- [assets/plan-template.md](assets/plan-template.md)
