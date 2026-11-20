# Skill Card: running-experiments

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to compare two or three architecturally distinct approaches by building and running prototype code for each, measuring them under the same conditions, and recommending one based on the evidence. It is written instructions plus an experiment template and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers for whom the best technical approach is genuinely uncertain and a head-to-head prototype comparison is worth the cost. Typical triggers: "should I use X or Y", "compare approaches", "which is faster". The skill is optional and says not to use it when the answer is already clear.

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. A prototype the agent writes may itself need credentials, and installing a library from a private package index may need an index token; the skill provides none.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: read`. The skill has the agent build and run every approach it compares (the Iron Law), which for a library comparison means fetching and installing the packages under test. The skill does not name a package manager or an index. Prototype code the agent writes could also use the network.
- `capability-shell: runs-commands`. The skill directs the agent to create a branch or scratch directory (`git checkout -b experiment-<slug>` or `.experiments/<slug>`) and to run prototypes, benchmarks and tests (for example `python benchmark.py`, `pytest`). It runs code that the agent has just written, with the user's permissions.
- `capability-file: write`. The skill directs the agent to write prototype code in the isolated branch or directory and to write `docs/rse/specs/experiment-<slug>.md`.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: the agent executes freshly written, unreviewed code and can leave a stray branch or scratch directory behind. Putting prototype source in a temporary branch or scratch directory separates the files, but it does not limit execution: the code still runs with the user's permissions against the real filesystem and network.
Mitigation: none in the skill for execution itself. The skill requires the location of the code to be documented, which helps cleanup. Review the code before running anything that touches real data or systems, or run it in a sandbox or container.

Risk: package installation. Comparing libraries means installing packages chosen by the agent, by name and version, into the user's environment, which is a supply-chain and environment-mutation risk (a mistyped or malicious package, a changed global environment). The skill does not require an isolated environment, and `git checkout -b` also moves the user's HEAD.
Mitigation: the skill requires the environment to be held constant across approaches and the conditions to be captured per `ai-research-workflows:ensuring-reproducibility`, so the packages and versions installed are recorded in the experiment document. Check that list, install into a throwaway virtual environment, container or the scratch directory, and commit or stash uncommitted work before the branch is created.

Risk: a comparison that looks measured but is not, for example one approach run and the other estimated, or a single noisy timing.
Mitigation: the skill's rule is that every compared approach must be built and run. An approach that could not be built is labelled an unverified assumption. Benchmarks are run several times, with variance reported, seeds fixed and inputs held constant.

## Output

**Output Type(s):** Code (prototypes, in isolation), Analysis, Files (Markdown).
**Output Format:** `docs/rse/specs/experiment-<slug>.md` following `assets/experiment-template.md`, with commands, outputs, a comparison matrix and a recommendation.
**Other Properties:** records failures and rejected approaches as well as successes.

## Version

Released with the `ai-research-workflows` plugin; see its `plugin.json` version.

## Ethics

The skill is about honest reporting: it forbids fabricating or estimating one side of a comparison, requires negative results and variance to be reported, and requires caveats on where the recommendation may not hold. Results from small prototypes are indicative, not general. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [assets/experiment-template.md](assets/experiment-template.md)
