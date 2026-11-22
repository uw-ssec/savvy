# Conventions: Documents and Deferral

## Document naming & cross-references

All workflow documents are saved to `docs/rse/specs/` in the project root as
`research-<slug>.md`, `plan-<slug>.md`, `experiment-<slug>.md`,
`implement-<slug>.md`, `validation-<slug>.md`, and `handoff-<timestamp>-<slug>.md` (slug = lowercased,
hyphenated topic). These are committed, version-controlled artifacts — the
decision record lives in the repo. **Write** new documents to `docs/rse/specs/`;
when **reading** existing documents, search `docs/rse/specs/` first and fall back
to the legacy `.agents/` location (older layout). Legacy `prior-art-<slug>.md`
docs are still read when present.
Docs cross-link with relative markdown links so plan → research, implement → plan,
validation → plan+implement, and handoff → all of them form a navigable graph.
Each skill states its own naming and cross-reference rules.

## Deferral

Some concerns are better handled by specialist skills or plugins. Hand off to
them rather than re-implementing their guidance here. The targets outside this
plugin apply only if that plugin is installed.

| Concern | Defer to |
|---|---|
| Environments (pixi) | `scientific-python-development:pixi-package-manager` |
| Environments (uv) | the project's own uv setup and `uv.lock` (no dedicated skill here) |
| Tests | `scientific-python-development:python-testing` |
| Packaging | `scientific-python-development:python-packaging` |
| Documentation | `scientific-python-development:scientific-documentation` |
| Community / handoff readiness | `project-management:community-health-files` |
| Project handoff | `creating-handoffs` (this plugin); the `/project-management:project-handoff` command |
| Heavy multi-source research | a `deep-research` skill if your client provides one (not bundled here) |
