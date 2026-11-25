# Skill Card: running-experiments

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to compare two or three architecturally distinct approaches by building and running prototype code for each, measuring them under the same conditions, and recommending one based on the evidence. It is written instructions (a short `SKILL.md` that points to two reference files) plus an experiment template, and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers for whom the best technical approach is genuinely uncertain and a head-to-head prototype comparison is worth the cost. Typical triggers: "should I use X or Y", "prototype both", "compare approaches", "benchmark before committing", "which is faster on our data". Surveys of existing tools or papers belong to the `researching` skill. The skill is optional and says not to use it when the answer is already clear.

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. A prototype the agent writes may itself need credentials, and installing a library from a private package index may need an index token; the skill provides none.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: read`. The skill has the agent build and run every approach it compares (the Iron Law), which for a library comparison means fetching and installing the packages under test. The skill names no package manager; it tells the agent to install only the packages under comparison, from their official package index, pinned to an exact version. Prototype code the agent writes could also use the network.
- `capability-shell: runs-commands`. The skill directs the agent to create a scratch directory (`.experiments/<slug>`) or, on a clean working tree only, a branch (`git checkout -b experiment-<slug>`), and to run prototypes, benchmarks and tests (for example `python .experiments/<slug>/bench.py`, `pytest`). It runs code that the agent has just written, with the user's permissions.
- `capability-file: write`. The skill directs the agent to write prototype code in the isolated branch or directory and to write `docs/rse/specs/experiment-<slug>.md`.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: the agent executes freshly written, unreviewed code and can leave a stray branch or scratch directory behind. Putting prototype source in a temporary branch or scratch directory separates the files, but it does not limit execution: the code still runs with the user's permissions against the real filesystem and network.
Mitigation: none in the skill for execution itself. The skill keeps prototypes out of the package (`src/`), forbids committing them to the user's working branch, requires their location to be documented, and tells the agent to ask before deleting them, which helps cleanup. Review the code before running anything that touches real data or systems, or run it in a sandbox or container.

Risk: package installation. Comparing libraries means installing packages chosen by the agent, by name and version, into the user's environment, which is a supply-chain and environment-mutation risk (a mistyped or malicious package, a changed global environment). The skill limits installs to the packages under comparison, from their official index and pinned to an exact version, and asks for an isolated environment where the project allows it, but cannot verify a package's contents. `git checkout -b` moves the user's HEAD, so the skill allows the branch only on a clean working tree and otherwise uses the scratch directory.
Mitigation: none in the skill prevents a bad install. The skill requires the environment to be held constant across approaches and the conditions to be captured per `ai-research-workflows:ensuring-reproducibility`, so the packages and versions installed are recorded in the experiment document. Check that list, and install into a throwaway virtual environment, container or the scratch directory.

Risk: a comparison that looks measured but is not, for example one approach run and the other estimated, or a single noisy timing.
Mitigation: the skill's rule is that every compared approach must be built and run. An approach that could not be built, or that the user asked not to run, is labelled an unverified assumption, and the agent offers to run the real comparison. Benchmarks are run several times, with variance reported, seeds fixed and inputs held constant.

## Output

**Output Type(s):** Code (prototypes, in isolation), Analysis, Files (Markdown).
**Output Format:** `docs/rse/specs/experiment-<slug>.md` following `assets/experiment-template.md`, with commands, outputs, a comparison matrix and a recommendation.
**Other Properties:** records failures and rejected approaches as well as successes.

## Version

Released with the `ai-research-workflows` plugin. The version is the release tag in the signed archive's name, `ai-research-workflows--running-experiments-<version>.tar.gz`, without the `v` (for example `26.11.0`). The plugin's `plugin.json` shows the release in which the plugin last changed, so it can be older than the archive.

## Ethics

The skill is about honest reporting: it forbids fabricating or estimating one side of a comparison, requires negative results and variance to be reported, and requires caveats on where the recommendation may not hold. Results from small prototypes are indicative, not general. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [references/running-the-comparison.md](references/running-the-comparison.md)
- [references/reporting.md](references/reporting.md)
- [assets/experiment-template.md](assets/experiment-template.md)
