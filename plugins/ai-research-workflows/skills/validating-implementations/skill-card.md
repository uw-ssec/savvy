# Skill Card: validating-implementations

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to check a completed implementation against every success criterion in its plan: read the plan, inspect the code, re-run each automated verification command itself, investigate each failure to a root cause, list manual checks for a human, and write a validation report without changing the code under review. It is written instructions plus two references (process detail and report templates) and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who need an implementation checked against its plan before shipping. Typical triggers: "validate the implementation", "verify it matches the plan", "check before PR or merge", "all tests pass, just confirm it".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. A plan's verification commands may need their own credentials; the skill does not provide them.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access. Verification commands taken from a plan may still use the network.
- `capability-shell: runs-commands`. The skill directs the agent to run `git log`, `git diff --stat`, `git rev-parse --short HEAD`, and every command in the plan's "Automated Verification" section verbatim (for example `pixi run pytest`). It runs whatever the plan lists, with the user's permissions. It also runs a baseline test command that the plan or the project documents, re-runs failing checks to find their root cause, and for research code re-runs result-producing code to confirm that reported numbers reproduce.
- `capability-file: write`. The skill directs the agent to write `docs/rse/specs/validation-<slug>.md`, overwriting a previous validation of the same plan, and to read the plan and the code. It writes this file even when the user asks for a chat-only summary, because the file is the verdict's record; if the user forbids writing files, it writes none and says the verdict has no record. It tells the agent not to edit the code, tests, data or documentation under review.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`. An earlier acceptance of an `Anti-Refusal Statement (AR2)` false positive was removed when the fresh-session wording it matched was rewritten.

Risk: running the plan's verification commands executes whatever the plan says, so a malicious or mistaken plan is run.
Mitigation: read the plan before validation. The skill itself does not vet the commands, and that review does not reach the baseline test run or the re-run of research code, which are not in the plan.

Risk: re-running result-producing research code can mean long, costly training or analysis runs, and can overwrite the output artifacts or reported results being checked.
Mitigation: the process reference tells the agent to write long or costly re-runs to a separate output location so the original results stay intact. The skill does not limit run time or cost; back up important outputs before validation.

Risk: a verdict based on someone else's report or on plan checkmarks.
Mitigation: the skill's Iron Law is that no verdict is given without fresh output the agent produced itself. Checkmarks and teammates' reports count as claims, manual items are never marked done without user confirmation, and the report separates automated from manual results.

Risk: the report overwrites an earlier validation file.
Mitigation: the skill records provenance (plan, commit, date) in the report, and git history keeps earlier verdicts if the file was committed.

## Output

**Output Type(s):** Analysis, Files (Markdown).
**Output Format:** a validation report written to `docs/rse/specs/validation-<slug>.md` and presented inline, with Implementation Status, Automated Verification Results, Code Review Findings, Manual Testing Required and Recommendations.
**Other Properties:** includes provenance (plan, commit, date) and a References section.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--validating-implementations-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

Validation results are relied on to decide whether work ships, so the skill requires verdicts to rest on evidence the agent observed, deviations to be reported as facts and not guessed intent, and for research code, reported numbers to be re-run within stated tolerance. A passing report does not replace human review. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/validation-process.md](references/validation-process.md)
- [references/report-templates.md](references/report-templates.md)
