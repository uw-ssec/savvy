# Skill Card: implementing-plans

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to execute an approved phased implementation plan (`docs/rse/specs/plan-*.md`): review the plan critically, confirm the working branch, implement one phase at a time, run the plan's automated checks, pause for human manual verification, and write an implementation summary. It is written instructions plus templates and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who have an approved plan and want an agent to write the code. Typical triggers: "implement the plan", "execute the plan", "start building".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. A plan the user supplies may call for its own credentials; the skill does not provide or manage them.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access. Commands taken from a plan may still use the network.
- `capability-shell: runs-commands`. The skill directs the agent to run the commands in the plan's "Automated Verification" section (for example `make test`, `pytest`, `mypy`). The agent runs whatever the plan lists, with the user's permissions, so a plan is effectively an instruction set to be trusted or reviewed.
- `capability-file: write`. The skill directs the agent to edit project source files, tick checkboxes in the plan file, and write `docs/rse/specs/implement-<slug>.md`.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: executing a plan that is wrong, stale or unsafe changes the codebase and runs its commands.
Mitigation: the skill requires the agent to review the plan critically before any code is written. This review is the agent's own; if it finds nothing to raise, the agent proceeds, so it is not a human gate. It requires a stop and a mismatch report when the code differs from the plan, and it forbids starting on `main` or `master` without explicit user consent.

Risk: when resuming a plan, the skill says to "Trust that completed work is done" and to re-verify earlier phases only if tests fail, files are missing or something looks inconsistent. A stale or wrong checkmark is therefore built on without being checked.
Mitigation: the skill's conditions for re-verifying (failing tests, missing files, inconsistencies) are the only safeguard. Check the plan's existing checkmarks against the code before resuming work that depends on them.

Risk: automated checks pass while manual criteria are untested.
Mitigation: the skill requires a pause for human verification after each phase (except consecutive phases the user explicitly requested) and forbids checking off manual items the user has not confirmed.

## Output

**Output Type(s):** Code (edits to project files), Files (updated plan, implementation summary).
**Output Format:** edits in place; `docs/rse/specs/implement-<slug>.md` from `assets/implement-template.md`.
**Other Properties:** records deviations from the plan and verification results.

## Version

Released with the `ai-research-workflows` plugin; see its `plugin.json` version.

## Ethics

The skill keeps a person in the loop at phase boundaries and requires deviations from the plan to be reported to them before the agent continues. For research code it directs the agent to capture provenance for results with the `ensuring-reproducibility` skill. Review changes before merging; the agent's report of passing checks is not a substitute. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [assets/implement-template.md](assets/implement-template.md)
- [references/templates.md](references/templates.md)
