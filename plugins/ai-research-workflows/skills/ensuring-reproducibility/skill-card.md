# Skill Card: ensuring-reproducibility

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to record the provenance of a result (environment and lockfile, code commit, hardware, data versions or hashes, seeds, configuration, exact commands) and to reproduce it in a clean environment before calling it reproducible. It is written instructions only and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Researchers and research software engineers who need a result, experiment or analysis to be reproducible by others or by a future session. Typical triggers: "make this reproducible", "capture provenance", "why can't I reproduce X".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. Remote datasets the user points it at may need their own access, which the skill does not handle.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: read`. The skill directs the agent to record data URLs and retrieval dates and to reproduce from a pinned lockfile in a fresh environment (for example `uv sync --frozen` or a clean pixi environment). That installs packages and may download recorded data from the network.
- `capability-shell: runs-commands`. The agent runs commands to read the commit hash (`git rev-parse HEAD`), and runs the recorded commands (for example training and evaluation scripts) in a clean environment. It will run whatever those recorded commands say, with the user's permissions.
- `capability-file: write`. The skill directs the agent to append a `## Reproducibility` section to an existing artifact in `docs/rse/specs/` or to create `docs/rse/specs/reproducibility-<slug>.md`.
- `capability-environment: none`. No environment variables are read as inputs.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: re-running recorded commands can be slow or costly (long jobs, GPUs) and downloads and installs third-party packages.
Mitigation: the skill allows a minimal reproduction (smaller subset, fewer steps, one seed). Review the commands before they are run.

Risk: a provenance record can look complete without having been verified.
Mitigation: the skill states that an unreproduced record is a hypothesis. It permits deferral only when a fresh run is technically impossible, never for lack of time, and requires any tolerance to be documented.

## Output

**Output Type(s):** Files (Markdown), plus command runs in a clean environment.
**Output Format:** a `## Reproducibility` section appended to `docs/rse/specs/experiment-<slug>.md` or `implement-<slug>.md`, or a new `docs/rse/specs/reproducibility-<slug>.md`.
**Other Properties:** includes the outcome of the reproduction attempt (success, failure, tolerance applied).

## Version

0.2.0 (the `ai-research-workflows` plugin manifest version; this skill is not versioned separately).

## Ethics

The skill supports research integrity: a reported number should be backed by a record someone else can follow, and a failed or partial reproduction should be reported as such rather than omitted. It does not make a result correct; it only shows whether it can be re-obtained. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
