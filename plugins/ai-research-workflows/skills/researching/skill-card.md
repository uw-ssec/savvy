# Skill Card: researching

Format follows NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI). Sections not applicable to a plain-instruction skill (evaluation agent, tasks, metrics, results) are omitted.

## Description

Instructs an agent to investigate the current codebase (call paths, module dependencies), external prior art (papers, tools, methods, documentation), or both, and to synthesize one research document that feeds planning. It is written instructions, two reference documents and a template, and ships no code.

## Owner

SSEC Engineering Team

## License

BSD-3-Clause (as declared in the plugin manifest, `plugins/ai-research-workflows/plugin.json`).

## Use Case

Developers and researchers who need to understand how existing code works, or what prior work and tools exist, before planning or changing something. Typical triggers: "how does X work", "where is X implemented", "what libraries exist for X", "has this been done before".

## Deployment Geography

Not applicable. The skill is plain instructions with no service component. It can be used anywhere the user's agent client runs. The prior-art pass uses whatever web search and fetch tools the user's client provides, so what it can reach depends on that client and network.

## Credentials

Requires API key or external credential: No. Credential type: none. The skill declares `capability-environment: none`. The user's client may need its own credentials for its web search tool; the skill does not handle them.

## Risks and Mitigations

Capability declarations (`metadata` in `SKILL.md`) and what each implies:

- `capability-network: read`. The prior-art pass directs the agent to search the web and fetch pages (papers, documentation, blog posts) using the client's tools. It reads from the network; it does not direct writes to it.
- `capability-shell: runs-commands`. The codebase pass directs the agent to search and read the repository (`grep`, `find`, ripgrep) and the skill records the commit hash (`git rev-parse --short HEAD`). The agent runs these with the user's permissions.
- `capability-file: write`. The skill directs the agent to write `docs/rse/specs/research-<slug>.md` and to read project files and existing documents.
- `capability-environment: none`. No environment variables are read.
- `capability-mcp: none`. No MCP tools are used.

Accepted security findings: none for this skill in `.github/skill-security-accepted.yml`.

Risk: fetched web pages are untrusted text and can contain misleading claims or instructions aimed at the agent. The skill does not tell the agent to treat fetched content as untrusted.
Mitigation: none in the skill for injected instructions. The primary-source citation rule, the labelling of secondary sources and the search for contradicting evidence address the quality of sources, not injection. Users should treat any instruction found in fetched content as data. The document is not reviewed by a person before planning in every mode: in Collaborative mode the skill waits for the user's review, but in Direct mode it presents the document, notes that it is ready for review and proceeds.

Risk: when both passes are in scope, the agent reads private code and then writes web search queries (`references/prior-art-research.md`), so internal identifiers, architecture details or unpublished research topics can leave the machine as query text.
Mitigation: none in the skill. Scope the request to the internal pass only, or tell the agent to generalise its queries, when the codebase or topic is confidential.

Risk: the findings can be wrong or go stale, which then misleads the plan built on them.
Mitigation: every code finding must cite `file:line`, the commit SHA and date are recorded, and the skill has the agent present findings and offer the document for user review before moving on.

## Output

**Output Type(s):** Analysis, Files (Markdown).
**Output Format:** `docs/rse/specs/research-<slug>.md` following `assets/research-template.md`.
**Other Properties:** `file:line` anchors for code findings; citations for prior-art claims; gaps named explicitly.

## Version

Released with the `ai-research-workflows` plugin; see its `plugin.json` version.

## Ethics

Research findings feed design decisions and sometimes published work, so the skill requires claims to be traceable to sources, requires looking for evidence against the main finding, and requires gaps to be named instead of smoothed over. Cited material remains subject to its authors' licenses and attribution norms. Developers should confirm the skill fits their team's policies before adoption.

## Reference(s)

- [SKILL.md](SKILL.md)
- [assets/research-template.md](assets/research-template.md)
- [references/codebase-research.md](references/codebase-research.md)
- [references/prior-art-research.md](references/prior-art-research.md)
