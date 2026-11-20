# Skill Card: validating-implementations

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to check a completed implementation against every success criterion in its plan: read the plan, inspect the code, re-run each automated verification command itself, list manual checks for a human, and write a validation report. It is written instructions plus a report-template reference and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who need an implementation checked against its plan before shipping. Typical triggers: "validate the implementation", "verify it matches the plan", "check before PR".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. A plan's verification commands may need their own credentials; the skill does not provide them.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access. Verification commands taken from a plan may still use the network.
- `capability-shell: runs-commands`. The skill directs the agent to run `git log`, `git diff --stat`, and every command in the plan's "Automated Verification" section (for example `make test`, `pytest`, `mypy`, `npm run lint`). It runs whatever the plan lists, with the user's permissions. It also runs a baseline test command that does not come from the plan (`make test`, `pytest tests/ -v` or `npm test`), and for research code it directs the agent to re-run result-producing code to confirm that reported numbers reproduce.
- `capability-file: write`. The skill directs the agent to write `docs/rse/specs/validation-<slug>.md`, overwriting a previous validation of the same plan, and to read the plan and the code.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings, from `.github/skill-security-accepted.yml`:

- `Anti-Refusal Statement (AR2)` (high), in `SKILL.md`. This is a false positive. The accepted-findings file attributes the match to the guidance for reviewing in a fresh session, which says to note deviations "without judging them". That asks the reviewer to report deviations as observable facts and not speculate about intent. It does not ask the agent to suppress warnings or refusals. The nearby line about having no memory of implementation decisions describes a fresh session. The acceptance is pinned to the SHA-256 of `SKILL.md`, so any edit to that file requires a new review.

Risk: running the plan's verification commands executes whatever the plan says, so a malicious or mistaken plan is run.
Mitigation: read the plan before validation. The skill itself does not vet the commands, and that review does not reach the baseline test run or the re-run of research code, which are not in the plan.

Risk: re-running result-producing research code can mean long, costly training or analysis runs, and can overwrite the output artifacts or reported results being checked.
Mitigation: none in the skill. Back up the original outputs, or point the re-run at a separate output location, before validation.

Risk: a verdict based on someone else's report or on plan checkmarks.
Mitigation: the skill's Iron Law is that no verdict is given without fresh output the agent produced itself. Checkmarks and teammates' reports count as claims, manual items are never marked done without user confirmation, and the report separates automated from manual results.

Risk: the report overwrites an earlier validation file.
Mitigation: the skill records provenance (plan, commit, date) in the report, and git history keeps earlier verdicts if the file was committed.

## Output

**Output Type(s):** Analysis, Files (Markdown).
**Output Format:** a validation report written to `docs/rse/specs/validation-<slug>.md` and presented inline, with Implementation Status, Automated Verification Results, Code Review Findings, Manual Testing Required and Recommendations.
**Other Properties:** includes provenance (plan, commit, date) and a References section.

## Version

Released with the `ai-research-workflows` plugin; see its `plugin.json` version.

## Ethics

Validation results are relied on to decide whether work ships, so the skill requires verdicts to rest on evidence the agent observed, deviations to be reported as facts and not guessed intent, and for research code, reported numbers to be re-run within stated tolerance. A passing report does not replace human review. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/report-templates.md](references/report-templates.md)
