# Skill Trust Evidence: Pilot Design

Tracks [#293](https://github.com/uw-ssec/savvy/issues/293). Pilot scope: the
`supply-chain-security` and `ai-research-workflows` plugins.

## Intent

Give savvy's users, and the IT and security teams who support them, evidence
they can check before installing a skill. Two kinds of trust matter equally:

- **Safe to install:** what the skill can make an agent do, what risks it
  carries, and that the files they download are the files savvy published.
- **Actually helps:** measured with-versus-without-skill results on a public
  task set.

This is not an application for NVIDIA's "NVIDIA-Verified" stamp. NVIDIA's
artifact formats (SkillEvaluator output, skill cards, OMS signatures) are used
because they are good formats, not to satisfy NVIDIA. Savvy signs its own
releases with keyless Sigstore under the uw-ssec GitHub identity.

## Scope

16 skills:

| Plugin | Skills |
|---|---|
| `plugins/supply-chain-security` | `supply-chain-dependency-security`, `supply-chain-ecosystem-quirks`, `supply-chain-hardened-ci-cd`, `supply-chain-incident-response`, `supply-chain-sbom-provenance`, `supply-chain-threat-awareness` |
| `plugins/ai-research-workflows` | `creating-handoffs`, `ensuring-reproducibility`, `hardening-research-code`, `implementing-plans`, `iterating-plans`, `planning-implementations`, `researching`, `running-experiments`, `using-research-workflows`, `validating-implementations` |

The other 60 skills are out of scope until the pilot is reviewed.

## Goals

1. Every skill in scope passes SkillEvaluator's full `validate` (Tier 1:
   schema, license, PII, Unicode, Semgrep/SkillSpector/Gitleaks security scan),
   or each high/critical finding is recorded as accepted with a reason.
2. Every skill in scope has a public eval task set at
   `<skill>/evals/evals.json`, including negative (should-not-trigger) cases.
3. Every skill in scope has a `BENCHMARK.md` from a SkillEvaluator Tier 3 run
   (agent with versus without the skill).
4. Every skill in scope has a `skill-card.md` (owner, license, use case,
   deployment geography, credentials, risks and mitigations, output, version,
   ethics).
5. Every skill in scope declares its capabilities (network, shell, file,
   environment, MCP) in its `SKILL.md` frontmatter.
6. Each release publishes a signed archive per skill, and a user can verify a
   download with one documented command.

## Non-goals

- NVIDIA signing, cataloguing or the NVIDIA-Verified stamp.
- Verifying a skill as installed on a user's disk ("after install"
  verification). The design must not block adding it later (see Signing).
- Benchmarks or skill cards for the other 60 skills.
- Replacing dokimi trigger/novelty testing (#235); this work is complementary.

## Anti-goals

- **Hiding weak results.** A skill that shows no lift, or loses to the
  baseline, publishes that result as it is. Evidence that only ever looks good
  is not evidence.
- **Benchmarks that block merges.** They are expensive and noisy; gating on
  them would make contributors re-run paid evals to land a typo fix.
- **Unreviewed generated content.** LLM-drafted eval cases and skill cards are
  reviewed by a person before merge. A plausible-looking card with wrong risks
  is worse than none.
- **Breaking any client.** Frontmatter or directory changes that make Claude
  Code, Codex, Gemini CLI, Copilot, Cursor, OpenCode or Hermes reject or
  mis-load a skill are not acceptable.

## Decisions

These were decided with the maintainer:

| Decision | Choice |
|---|---|
| Pilot scope | The two plugins above |
| Signer | Savvy, keyless Sigstore, uw-ssec identity; not NVIDIA |
| What "trust" means | Both "safe to install" and "actually helps", equally |
| When users verify | **Before install**: evidence on GitHub, signed release downloads. After-install verification deferred |
| Weak results | **Split**: security scan gates PRs; benchmarks are reported, never gating |
| Signing mechanism | **OpenSSF model signing** (`model_signing`, OMS format) per skill directory |
| Capability meaning | What the skill **directs the agent to do** (these skills ship no executable code). Short string values; checked by a reviewer, not CI |
| Skill author | `metadata.author` as `Name <email>` with a shared, public SSEC team address; if none exists, one repo-wide SkillEvaluator policy override of `SCHEMA.author_missing`, recorded with its reason |
| Evidence files and versioning | `evals/`, `BENCHMARK.md` and `skill-card.md` do not count as plugin changes; `docs/versioning.md` is updated to exclude them |
| Benchmark results PR | Workflow pushes a branch; a person opens the PR (no new secret) |
| Approving accepted findings | CODEOWNERS on the accepted-findings file, plus "require code owner review" in branch protection (maintainer turns this on) |
| Release mechanics | Signing runs in a release workflow on Release published; the `release` skill is brought in line with calendar versioning; unsigned zips stop for the pilot plugins |
| Benchmark budget | Default: one agent (claude-code), one model, 3 attempts per case; wider runs on request |

## Approaches considered (signing)

- **A. GitHub artifact attestations.** Tar each skill, run
  `actions/attest-build-provenance`; users run `gh attestation verify`.
  Least code, familiar command, includes build provenance. Signs an opaque blob,
  so it can't later verify an unpacked or installed skill; after-install
  verification would need a second system.
- **B. OpenSSF model signing (chosen).** Sign each skill directory with
  `model_signing sign sigstore`, producing `skill.oms.sig` covering every file;
  pack directory plus signature into the release archive. Users unpack and run
  `model_signing verify sigstore` against the uw-ssec workflow identity. The
  same signature and command later work on an installed copy, and a failed
  verification names the changed file. Less familiar tool; no build-provenance
  record (could be layered on with A's action later).
- **C. `cosign sign-blob` bundles.** Rejected: same blob-only limitation as A
  without A's provenance.

## Design

### 1. Security scan gate (PR time)

- Extend `.github/workflows/skill-quality-check.yml` so that, for changed
  skills in the two pilot plugins, it also runs `skillevaluator validate
  --tiers 1` through a pixi task, as `quality-check` already does (single
  SkillEvaluator pin in `pixi.toml`). `--tiers 1` matters: by default
  `validate` also runs Tiers 2 and 3 and generates missing evals into the
  skill folder.
- Semgrep, Gitleaks and SkillSpector are not in the `ci` environment today;
  pin them through pixi.
- The gate fails on any high or critical finding not recorded as accepted.
- Accepted findings live in a reviewed file inside the repo, one entry per
  finding with the skill, the finding identity and a one-line reason. The file
  is covered by a new CODEOWNERS entry so only maintainers can approve
  acceptances.
- The missing-author finding (`SCHEMA.author_missing`, HIGH in SkillEvaluator's
  default profile) is resolved as set out in Decisions, not by 16 identical
  acceptances.
  `supply-chain-incident-response` and `supply-chain-threat-awareness` are
  expected to need entries: they quote real attack commands on purpose.
- Before wiring this up, triage every finding across the 16 skills: fix, or
  accept with a reason.
- `validate`'s own report goes to the job summary and an uploaded artifact,
  as `quality-check`'s does today.

### 2. Eval task sets

- One `evals/evals.json` per skill in the agentskills.io format SkillEvaluator
  expects (`skill_name`, `evals[]` with `id`, `prompt`, `expected_output`,
  `assertions`), plus `evals/config.yml` where defaults need overriding.
- Drafted with `skillevaluator create-eval-dataset`, then reviewed and edited
  by a person. Each set includes at least one should-not-trigger case.
- Written fresh: `supply-chain-security` has no cases in the private
  testcases repo, and `ai-research-workflows`' six cases target the removed
  `research-workflow-management` skill. They may be mined for prompts.
- Public by design. Tier 1 skips `evals/`, so these files don't affect the scan.

### 3. Benchmarks (reported, not gating)

- A manually triggered workflow (modelled on "Evaluate All Skills") runs
  SkillEvaluator Tier 3 for selected skills: Harbor in Docker on a GitHub
  runner, models reached through the existing LiteLLM proxy.
- It writes each skill's `BENCHMARK.md` with SkillEvaluator's reporter and
  pushes the results to a branch; a person opens the pull request, so required
  checks run and result changes are reviewed and dated in git history. Keep
  the job that holds LiteLLM secrets separate from the job that pushes.
- Defaults: claude-code, one model, 3 attempts per case. Workflow inputs
  narrow or widen skills, agents and models.
- Run before each release that changes a pilot skill, and on demand.
- A skill whose benchmark fails or is inconclusive keeps that result in
  `BENCHMARK.md`, with an optional maintainer note on why. The release notes
  list the benchmark verdict for each pilot skill.

### 4. Skill cards

- One `skill-card.md` per skill, started from NVIDIA's Skill Card generator
  and reviewed by a person. Owner: SSEC Engineering Team. License: the
  plugin's license.
- "Risks and mitigations" must agree with the accepted-findings file and with
  the declared capabilities.

### 5. Capability declarations

- Declare network, shell, file, environment and MCP use in `SKILL.md`
  frontmatter under `metadata`, the key the Agent Skills spec reserves for
  extensions. Four supply-chain skills already carry string-valued `metadata`
  (`references`, `assets`), and `plugins-check` requires `metadata` values to
  be strings.
- A declaration states what the skill directs the agent to do. Suggested
  shape: one key per capability (e.g. `capability-shell: runs-commands`,
  `capability-network: none`) with values from a small fixed set such as
  `none`, `read`, `write`, `runs-commands`; the builder fixes the exact set and
  documents it. A reviewer checks the values against the skill's content.
- **Prerequisite:** confirm that every client savvy supports (see
  `docs/install.md` support matrix) loads a skill with the new keys, and that
  `pixi run plugins-check` and `claude plugin validate --strict` pass. If a
  loader rejects the shape, stop and bring the alternatives back to the
  maintainer.

### 6. Release signing

- A release workflow runs when a GitHub Release is published. It holds the
  only `id-token: write` permission, follows the repository's own hardened-CI
  rules (SHA-pinned actions, least-privilege permissions), and pins
  `model_signing` through pixi.
- For each pilot skill, from a clean checkout of the tag: copy the skill
  directory, sign it with `model_signing sign sigstore` (keyless, the
  workflow's OIDC identity), write `skill.oms.sig` into the copy, pack it as
  `<plugin>--<skill>-<version>.tar.gz`, and attach it to the Release.
- Signing is the last step. Nothing may write into a skill directory after
  signing, or strict verification fails.
- Signatures are not committed to the repository in this phase.
- Stop attaching unsigned zips for the two pilot plugins, so no unverifiable
  copy sits next to a signed one. Update the `release` skill to calendar
  versioning (`docs/versioning.md`) and to the new workflow.
- `v26.11.0` ships as planned; signing starts with the first release after
  the pilot lands.
- Document the verify command in `docs/trust-and-safety.md`, alongside how to
  read a skill card and a `BENCHMARK.md`. The `--identity` value contains the
  release tag, so document it as a template with the tag filled in by the
  user, plus the `--identity_provider` value.

### 7. Versioning

- Update `docs/versioning.md` so changes only under a skill's `evals/`,
  `BENCHMARK.md` or `skill-card.md` don't count as a plugin change, and make
  the changed-set command in the doc (and the `release` skill) exclude them.

### Later (not in this pilot)

After-install verification: commit `skill.oms.sig` into each skill directory
at release, and resolve copy-based installs that add files (#256). Expanding to
the other 60 skills.

## Constraints

- Pixi is the only package manager; SkillEvaluator and `model_signing` are
  pinned in `pixi.toml` (`ci` environment).
- Skills stay self-contained: every new file (`evals/`, `skill-card.md`,
  `BENCHMARK.md`) lives inside its skill directory.
- New files must not trip existing CI (`validate-plugins.yml`, link checks,
  `pixi run check-all`).
- Benchmark runs cost API spend through the LiteLLM proxy; the workflow takes
  skill and model inputs so a run can be narrowed.
- The local pixi environments currently fail with "the environment directory
  has moved" (the repo was renamed from `rse-plugins`); remove `.pixi/envs` and
  reinstall before running anything locally.

## Left to the builder

- Exact format and location of the accepted-findings file, and how the gate
  matches findings to it (SkillEvaluator has no built-in baseline file).
- The pixi task names and whether `validate` joins the existing job or runs as
  a second job.
- Which agents and models the benchmark workflow runs by default.
- The release archive naming details, and whether Release notes are generated
  or hand-written from the benchmark verdicts.
- The exact capability value set (see Design §5).
- Order of work. Suggested: scan triage and gate (with CODEOWNERS) →
  capabilities check → skill cards → eval sets → versioning exclusion →
  benchmarks → release signing.
