# Skill Card: hardening-research-code

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to make research and scientific code trustworthy by stating explicit correctness criteria and backing them with tests: reference or analytic checks, numerical tolerances, regression baselines, stability checks and invariant checks. It is written instructions only and ships no code. Test mechanics are deferred to the `scientific-python-development:python-testing` skill.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Researchers and research software engineers who need code to be verifiably correct, regression-safe and numerically stable. Typical triggers: "harden this code", "is this numerically correct", "add regression tests vs known results".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: none`. The skill does not direct any network access.
- `capability-shell: runs-commands`. The skill directs the agent to run the test suite, and to run each correctness test while its expected value or input is deliberately perturbed to confirm it fails. The agent runs these with the user's permissions, and test code can do anything the project code can.
- `capability-file: write`. The skill directs the agent to add or edit test files, reference or golden data files and notes on tolerances.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: tests that pin the current output can lock in a wrong result and make it look verified.
Mitigation: the skill forbids calling pinned output a verified baseline until it is checked against an independent reference or invariant. Otherwise the baseline must be labelled `UNVERIFIED`.

Risk: the "independent reference" (an analytic limit, a synthetic case, an invariant) is usually derived by the same agent that writes the tests. If that derivation is wrong, the skill's own rule then lets the baseline be called verified.
Mitigation: the skill requires a reference to be independent of the code under test, but it does not require a person to check it. Have a person review the stated correctness criterion and its derivation before a baseline is relied on.

Risk: a tolerance chosen to make a test pass hides a bug.
Mitigation: the skill says to derive tolerances from the numerics, to document the justification, and never to tune them to the result.

Risk: the agent edits a test's expected value while checking that it fails and does not restore it.
Mitigation: the skill's workflow says to restore the original after seeing the test fail. Review the diff.

## Output

**Output Type(s):** Code (tests), Files (reference data, tolerance notes).
**Output Format:** test files and versioned reference data in the user's repository.
**Other Properties:** each test states its correctness criterion; each baseline is verified or labelled `UNVERIFIED`.

## Version

Released with the `ai-research-workflows` plugin; see its `plugin.json` version.

## Ethics

For scientific code, wrong results can propagate into published findings. The skill treats "the output looks plausible" as insufficient and requires unverified baselines to be labelled as such, so readers are not misled about what has been checked. A passing test suite shows the stated criteria hold; it does not show the science is right. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
