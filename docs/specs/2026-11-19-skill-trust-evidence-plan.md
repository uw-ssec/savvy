# Skill Trust Evidence Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the 16 skills in `supply-chain-security` and `ai-research-workflows` a gating security scan, declared capabilities, skill cards, public eval sets, reported benchmarks, and Sigstore-signed release archives.

**Architecture:** One small repo script, `.github/scripts/skill_trust.py`, owns the pilot skill list and every deterministic check (security gate, evidence check, changed-plugin set, release staging/packing), tested with pytest like the other CI scripts. SkillEvaluator (already pinned in `pixi.toml`) does the scanning and benchmarking; `model_signing` does the signing. Three workflows wire it up: the existing skill-quality check gains a security job, a new manual benchmark workflow, and a new release-signing workflow.

**Tech Stack:** Python 3.12, pytest, pixi (`ci` env), SkillEvaluator `5320d93`, Semgrep, Gitleaks, SkillSpector, OpenSSF `model_signing`, GitHub Actions.

**Spec:** `docs/specs/2026-11-19-skill-trust-evidence-design.md`

## Global Constraints

- Pixi is the only package manager. Every new tool is pinned in `pixi.toml` `[feature.ci.*]`; never `pip`/`conda`/`venv`.
- `pixi run check-all` passes at the end of every task.
- Pilot plugins, exactly: `supply-chain-security`, `ai-research-workflows` (both under `plugins/`). Nothing outside them gets evidence files.
- Every new per-skill file lives inside its skill directory; no `../` links out of a skill.
- `metadata` values in `SKILL.md` frontmatter are strings (enforced by `plugins-check`).
- Gate blocks on `high` or `critical` only. Benchmarks never gate anything.
- Workflows: actions pinned to 40-char SHAs, `permissions: {}` at top level, least privilege per job, `persist-credentials: false` unless a job must push.
- Signing is the last write to a staged skill directory. Signatures are not committed to the repo.
- `v26.11.0` ships without signing; nothing here blocks it.
- Generated or LLM-drafted content (eval cases, skill cards) is reviewed by a person before merge.
- AI-assisted commits end with an `Assisted-by: <harness>:<model>` trailer (see the `commit` skill); never `Co-Authored-By:` for a tool or an agent-added `Signed-off-by:`. Work on a branch, never `main`.

## Review Focus

1. **A scanner is missing or crashes.** SkillEvaluator reports `overall_status: "incomplete"`; the gate must fail, never pass on an empty findings list. (Task 2 test)
2. **An accepted finding's line is edited.** The acceptance stops matching and the finding blocks again; an acceptance never silently covers new content. (Task 2 test)
3. **`validate` exits non-zero only because of findings that are all accepted.** The gate passes; a missing report (crash) still fails. (Task 2 test)
4. **A file is added to or changed in a skill directory after signing.** Verification fails. (Task 11 test)
5. **A PR touches only non-pilot skills, or no skills.** The security job selects nothing and passes without running the scanner. (Task 2 test)

---

### Task 1: Pin the scanners, add the scan task and policy overlay

**Files:**
- Modify: `pixi.toml` (`[feature.ci.dependencies]`, `[feature.ci.pypi-dependencies]`, `[feature.ci.tasks]`)
- Modify: `pixi.lock` (regenerated)
- Create: `.github/skillevaluator-policy.yml`

**Interfaces:**
- Produces: pixi task `skill-security-scan` = `skillevaluator validate --tiers 1 --policy .github/skillevaluator-policy.yml -r cli,json`, called as `pixi run -e ci skill-security-scan <skill-dir> -o <out-dir>`. Writes one `skillevaluator-output-*.json` into `<out-dir>`.

- [ ] **Step 1: Repair the local environment.** The envs were built when the repo was named `rse-plugins`. Run `rm -rf .pixi/envs && pixi install -e ci`. Expected: `pixi run -e ci skillevaluator --version` prints a version.
- [ ] **Step 2: Pin Semgrep and Gitleaks from conda-forge and SkillSpector from its git repo at a fixed commit** (same style as the `skillevaluator` pin, with a comment saying `validate` needs them). Run `pixi install -e ci`.
- [ ] **Step 3: Write `.github/skillevaluator-policy.yml`** overlaying the `external` profile: `severity_overrides: { SCHEMA.author_missing: low }`, with a comment giving the reason (the SSEC Engineering Team is the author, recorded in each plugin's `plugin.json`; no public per-skill email is published) and noting that adding `metadata.author` later makes this override removable.
- [ ] **Step 4: Add the `skill-security-scan` task** as specified in Interfaces.
- [ ] **Step 5: Verify every scanner runs.** `pixi run -e ci skill-security-scan plugins/supply-chain-security/skills/supply-chain-hardened-ci-cd -o <scratch>/scan` (any directory outside the checkout). Expected: the JSON's `overall_status` is `"passed"` or `"failed"`, **not** `"incomplete"`, and `incomplete_scans` is `[]`. No `SCHEMA.author_missing` finding above `low`.
- [ ] **Step 6: `pixi run check-all`**, expected pass. Commit `build(ci): pin SkillEvaluator scanners and add skill-security-scan task`.

### Task 2: Security gate in `skill_trust.py`

**Files:**
- Create: `.github/scripts/skill_trust.py`
- Create: `.github/scripts/tests/test_skill_trust.py`
- Create: `.github/skill-security-accepted.yml` (empty list `[]` for now)

**Interfaces:**
- Produces (all in `skill_trust.py`):
  - `PILOT_PLUGINS: tuple[str, ...] = ("supply-chain-security", "ai-research-workflows")`
  - `is_pilot(skill_dir: str) -> bool`: true for `plugins/<pilot>/skills/<name>`.
  - `@dataclass(frozen=True) class Acceptance: skill: str; check_name: str; file_path: str; line_content: str; reason: str`. `file_path` is relative to the skill dir.
  - `load_acceptances(path: Path) -> list[Acceptance]`: raises `ValueError` on a missing field or empty `reason`.
  - `@dataclass class GateResult: blocking: list[dict]; accepted: list[dict]; stale: list[Acceptance]; incomplete: bool`. `passed` property = not blocking, not stale, not incomplete.
  - `gate(report: dict, skill: str, acceptances: list[Acceptance]) -> GateResult`: walks every finding in the report's per-validator results (fields `severity`, `check_name`, `file_path`, `line_content`). Only `high`/`critical` are considered. A finding is accepted when skill, `check_name`, skill-relative `file_path` and `line_content.strip()` all equal an entry's. `stale` = this skill's entries that matched nothing. `incomplete` = `report["overall_status"] == "incomplete"`.
  - CLI: `python .github/scripts/skill_trust.py select-pilot` reads skill dirs on stdin, prints the pilot ones. `python .github/scripts/skill_trust.py gate --reports DIR --skills FILE --accepted FILE` prints a Markdown summary table (skill, blocking, accepted, stale, result) and exits 1 if any skill fails or has no readable report. Report dir per skill is named as `skill-quality.py`'s `report_name()`.

- [ ] **Step 1: Write failing tests** in `test_skill_trust.py`, loading the module the way `conftest._load` does. Build minimal report dicts inline.
  - `test_is_pilot`: `plugins/supply-chain-security/skills/x` → True. `plugins/holoviz-visualization/skills/x` → False. `community-plugins/supply-chain-security/skills/x` → False.
  - `test_high_finding_blocks`: one `high` finding, no acceptances → `len(blocking) == 1`, `not passed`.
  - `test_medium_finding_ignored` → `passed`.
  - `test_matching_acceptance_passes` → `accepted` has 1, `passed`.
  - `test_edited_line_blocks_again`: acceptance `line_content` differs by one character → blocking (Review Focus 2).
  - `test_stale_acceptance_fails`: an entry for this skill that matches nothing → `stale` has 1, `not passed`.
  - `test_incomplete_report_fails`: `overall_status: "incomplete"`, no findings → `not passed` (Review Focus 1).
  - `test_load_rejects_empty_reason` → `ValueError`.
  - `test_cli_gate_missing_report_fails`: skill listed, no report dir → exit 1, row says no readable report (Review Focus 3).
  - `test_cli_gate_all_accepted_passes`: a report with only accepted high findings → exit 0 (Review Focus 3).
  - `test_select_pilot_filters`: stdin with one pilot and one non-pilot skill → only the pilot printed. Empty stdin → empty output (Review Focus 5).
- [ ] **Step 2:** `pixi run -e ci test-scripts`. Expected: the new tests FAIL (module missing).
- [ ] **Step 3: Implement `skill_trust.py`** to the Interfaces above. Use PyYAML for the acceptances file.
- [ ] **Step 4:** `pixi run -e ci test-scripts`, all pass. `pixi run check-all` passes.
- [ ] **Step 5: Commit** `feat(ci): add skill security gate for trust pilot`.

### Task 3: Triage findings across the 16 skills

**Files:**
- Modify: pilot `SKILL.md` and reference files, only where a finding is a real issue
- Modify: `.github/skill-security-accepted.yml`
- Create: `.github/CODEOWNERS`

**Interfaces:**
- Consumes: the `skill-security-scan` task (Task 1) and `skill_trust.py gate` (Task 2).

- [ ] **Step 1: Scan all 16 skills** into the scratchpad, one report dir per skill. Then run `skill_trust.py gate` over them. Expected: a table listing every blocking finding.
- [ ] **Step 2: Triage each blocking finding.** If it's a real problem (secret-like string, risky instruction), fix the file. If it's intentional, add an entry with a one-line `reason`. Expect entries for quoted attack commands in `supply-chain-incident-response` and `supply-chain-threat-awareness`. Never edit a skill only to dodge a scanner pattern if that changes its meaning.
- [ ] **Step 3: Create `.github/CODEOWNERS`** with one line giving `/.github/skill-security-accepted.yml` to the savvy maintainers team. Confirm the team handle with the maintainer before committing; don't guess it.
- [ ] **Step 4: Re-run the gate on all 16.** Expected: exit 0, no stale entries.
- [ ] **Step 5:** `pixi run check-all` passes. Commit `fix(skills): triage SkillEvaluator findings for trust pilot` (fixes and the acceptance file together).

### Task 4: Wire the gate into CI

**Files:**
- Modify: `.github/workflows/skill-quality-check.yml` (new job `security-scan`; update the header comment that says `validate` is tracked separately)
- Modify: `.github/workflows/test-ci-scripts.yml` (paths, if the step tests read the new job)
- Modify: `.github/scripts/tests/test_skill_trust.py` (step test)
- Modify: `CONTRIBUTING.md` ("Evaluating Skills" and the security review paragraph that says `validate` isn't run)

**Interfaces:**
- Consumes: `skill-quality.py select` → `skill_trust.py select-pilot` → `skill-security-scan` per skill → `skill_trust.py gate`.

- [ ] **Step 1: Write a failing step test** using `conftest.workflow_step`/`run_step`, as the existing workflow step tests do. With an empty selection, the job's gate step exits 0 and writes "_no pilot skills changed_" to the summary.
- [ ] **Step 2: Add the `security-scan` job.** Mirror the `quality-check` job: same checkout, setup-pixi pins and fresh `$RUNNER_TEMP/reports`. Also add `.github/skill-security-accepted.yml`, `.github/skillevaluator-policy.yml` and `.github/scripts/skill_trust.py` to the `pull_request.paths` list. Keep going past a scanner failure, then run `skill_trust.py gate` and write its output to `$GITHUB_STEP_SUMMARY`. Upload the reports as an artifact named `skill-security-reports`.
- [ ] **Step 3:** `pixi run -e ci test-scripts` passes. Validate the workflow with `pixi run -e ci check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/skill-quality-check.yml`.
- [ ] **Step 4: Update `CONTRIBUTING.md`.** For pilot skills, PRs now run the full Tier 1 scan, and high or critical findings block unless accepted in `.github/skill-security-accepted.yml`, which CODEOWNERS covers. Give the local command: `pixi run -e ci skill-security-scan <skill> -o <dir>`.
- [ ] **Step 5:** `pixi run check-all`. Commit `ci: gate pilot skills on SkillEvaluator Tier 1 security scan`.
- [ ] **Step 6: Hand off to the maintainer:** turn on "Require review from Code Owners" for `main`. Record in the PR description that this is outstanding.

### Task 5: Capability declarations

**Files:**
- Modify: `.github/scripts/skill_trust.py` (+ tests)
- Modify: the 16 pilot `SKILL.md` frontmatters
- Modify: `CONTRIBUTING.md` (document the keys)

**Interfaces:**
- Produces:
  - `CAPABILITIES: dict[str, frozenset[str]]`:
    - `capability-network`: `none`, `read`, `write`
    - `capability-shell`: `none`, `runs-commands`
    - `capability-file`: `none`, `read`, `write`
    - `capability-environment`: `none`, `read`
    - `capability-mcp`: `none`, `uses`
  - `check_capabilities(frontmatter: dict) -> list[str]` returns error strings. Each of the 5 keys must be present under `metadata`, and its value must be in its set.
  - Meaning, to document verbatim: a value states what the skill **directs the agent to do**, not what code it ships. `network: read` means it tells the agent to fetch pages or packages. `write` means it tells the agent to publish or upload. `environment: read` means it tells the agent to read environment variables or credentials.

- [ ] **Step 1: Check loader compatibility first.** Add the five keys to one pilot skill only. Then confirm it loads in each client in the `docs/install.md` support matrix that can be run locally, and that `pixi run -e ci plugins-check-claude` passes (`claude plugin validate --strict`). Record which clients you checked in the PR. **If any loader rejects the skill, stop and report back to the maintainer** (spec §5).
- [ ] **Step 2: Write failing tests.**
  - `test_capabilities_all_present_valid` → `[]`.
  - `test_capability_missing_key` → one error naming the key.
  - `test_capability_bad_value` (`capability-shell: yes`) → one error.
  - `test_capabilities_with_folded_description`: parse a real frontmatter that uses `description: >-` plus a `metadata` block. Keys are found, and `metadata` values stay strings.
- [ ] **Step 3: Implement `check_capabilities`.** Run the tests; they pass.
- [ ] **Step 4: Declare capabilities for all 16 skills.** Read each skill's content to choose its values. Example: `supply-chain-hardened-ci-cd` directs editing workflow files and running `gh`/`git`, so `file: write` and `shell: runs-commands`.
- [ ] **Step 5:** `pixi run check-all`. Commit `feat(skills): declare capabilities for trust pilot skills`.

### Task 6: Evidence check and skill cards

**Files:**
- Modify: `.github/scripts/skill_trust.py` (+ tests), `pixi.toml` (task `trust-check`; add to `check-all`'s `depends-on`)
- Create: `plugins/<pilot>/skills/<skill>/skill-card.md` × 16

**Interfaces:**
- Produces:
  - `SKILL_CARD_SECTIONS: tuple[str, ...]` = `("Owner", "License", "Use Case", "Deployment Geography", "Credentials", "Risks and Mitigations", "Output", "Version", "Ethics")`. These are H2 headings, matched case-insensitively.
  - `check_skill(skill_dir: Path) -> list[str]`: runs `check_capabilities`, checks the skill card has every section, and checks evals (Task 7; skipped when `require_evals=False`).
  - CLI: `skill_trust.py check [--no-evals]` checks every pilot skill and exits 1 on any error. Pixi task: `trust-check = "python .github/scripts/skill_trust.py check"`.

- [ ] **Step 1: Write failing tests.** `test_card_missing_section` returns an error naming "Ethics". `test_card_complete` returns `[]`. `test_check_cli_reports_every_skill` uses a tmp tree with two pilot skills, one broken, and expects exit 1 with the broken skill named.
- [ ] **Step 2: Implement the card check and the `check` CLI.** Tests pass.
- [ ] **Step 3: Write the 16 skill cards.** Start each from NVIDIA's Skill Card generator (`NVIDIA/Trustworthy-AI`, `Skill Card.md`) and fill it from the skill's content. Owner: SSEC Engineering Team. License: BSD-3-Clause (from `plugin.json`). Version: the plugin's manifest version. "Risks and Mitigations" must name every accepted finding for the skill in `.github/skill-security-accepted.yml` and must agree with its capability values.
- [ ] **Step 4:** With the cards done but evals not yet written, the `trust-check` task temporarily runs with `--no-evals`; Task 7 removes the flag. `pixi run check-all` passes, including `trust-check`.
- [ ] **Step 5:** A person reviews the 16 cards. Commit `docs(skills): add skill cards for trust pilot`.

### Task 7: Eval task sets

**Files:**
- Create: `plugins/<pilot>/skills/<skill>/evals/evals.json` × 16
- Modify: `.github/scripts/skill_trust.py` (+ tests), `pixi.toml` (drop `--no-evals`)

**Interfaces:**
- Produces: `check_evals(skill_dir: Path) -> list[str]`. `evals/evals.json` must be the agentskills.io object form: `skill_name` equals the directory name, and every case has `id`, `prompt`, `expected_output` and a non-empty `assertions`. The file needs at least 5 cases with ids `<skill>-NNN` (should trigger) and at least 1 with id `<skill>-neg-NNN` (should not trigger), and ids must be unique.

- [ ] **Step 1: Write failing tests.** `test_evals_valid` returns `[]`. `test_evals_no_negative` returns an error. `test_evals_wrong_skill_name` returns an error. `test_evals_duplicate_id` returns an error.
- [ ] **Step 2: Implement `check_evals`.** Wire it into `check_skill`. Tests pass.
- [ ] **Step 3: Draft each set** with `pixi run -e ci skillevaluator create-eval-dataset <skill> --full` (needs the LLM provider env; see Task 9 Step 1). Then edit each set to the shape above. For `ai-research-workflows`, mine prompts from the six `research-workflow-management` cases in the private testcases repo, but don't copy private text verbatim into the public files without the maintainer's OK. Negatives should be near-misses that belong to a sibling skill (for example, a dependency-pinning prompt as the negative for `supply-chain-incident-response`).
- [ ] **Step 4: Remove `--no-evals` from `trust-check`.** `pixi run check-all` passes. Re-run the Task 1 scan on one skill: Tier 1 still skips `evals/`.
- [ ] **Step 5:** A person reviews all 16 sets. Commit `test(skills): add public eval task sets for trust pilot`.

### Task 8: Evidence-only changes don't bump versions

**Files:**
- Modify: `.github/scripts/skill_trust.py` (+ tests), `docs/versioning.md`, `.claude/skills/release/SKILL.md`

**Interfaces:**
- Produces: `EVIDENCE_PATTERNS = ("skills/*/evals/**", "skills/*/BENCHMARK.md", "skills/*/skill-card.md")`, relative to a plugin dir. `changed_plugins(root: Path, since: str) -> list[str]` returns plugin dirs (`plugins/x`, `community-plugins/y`) with at least one changed path outside the evidence patterns. CLI: `skill_trust.py changed-plugins <prev-tag>`.

- [ ] **Step 1: Write failing tests** using a tmp git repo (reuse the `repo`/`commit` fixture pattern from `test_skill_quality.py`):
  - A change only to `skills/a/evals/evals.json` gives `[]`.
  - A change only to `skills/a/BENCHMARK.md` gives `[]`.
  - A change to `skills/a/SKILL.md` gives `["plugins/p"]`.
  - A change to both `SKILL.md` and `BENCHMARK.md` gives `["plugins/p"]`.
- [ ] **Step 2: Implement `changed_plugins`** with `git diff --name-only <since>..HEAD` and `fnmatch` on the plugin-relative path. Tests pass.
- [ ] **Step 3: Update `docs/versioning.md`.** Replace the `git diff` changed-set commands with `pixi run -e ci python .github/scripts/skill_trust.py changed-plugins <previous-tag>`, and add one paragraph explaining that evidence files (evals, benchmarks, skill cards) are not plugin changes. In the `release` skill, replace its semver step with the calendar versioning in `docs/versioning.md`, and use the same command for the changed set.
- [ ] **Step 4:** `pixi run check-all`. Commit `docs(versioning): exclude skill evidence files from plugin change detection`.

### Task 9: Benchmark workflow

**Files:**
- Create: `.github/workflows/benchmark-skills.yml`
- Modify: `pixi.toml` (task `skill-benchmark`), `.github/scripts/skill_trust.py` (+ tests), `.github/workflows/test-ci-scripts.yml` (paths)

**Interfaces:**
- Produces:
  - Pixi task `skill-benchmark` = `skillevaluator validate --tiers 3 --no-autopilot -a claude-code -r json`, called with `<skill> -o <dir>`. It writes `<dir>/BENCHMARK.md`.
  - `skill_trust.py collect-benchmarks --reports DIR --root .` copies each `<report_name(skill)>/BENCHMARK.md` to `<skill>/BENCHMARK.md` and prints the skills it updated. A skill with no `BENCHMARK.md` is listed as missing and left untouched; this is not an error, since benchmarks are advisory.
  - Workflow inputs: `skills` (comma-separated, empty means all 16 pilot skills), `model` (LiteLLM model id, default set in the workflow), `attempts` (default `3`).

- [ ] **Step 1: Find the provider settings.** Locally, with the LiteLLM proxy URL and key, find the env vars that make SkillEvaluator's claude-code agent use the proxy (`SKILL_EVAL_LLM_PROVIDER`, `ANTHROPIC_BASE_URL`, and others in `skillevaluator/provider_config.py`). Confirm with `skillevaluator doctor -a claude-code --verify-models`. Record the working env var set in the workflow file's comment.
- [ ] **Step 2: Write failing tests** for `collect-benchmarks`: one skill has a report, one doesn't; the first file is copied and the second is listed as missing.
- [ ] **Step 3: Implement `collect-benchmarks`.** Tests pass.
- [ ] **Step 4: Write the workflow.** Trigger: `workflow_dispatch` only. Job `run`: `contents: read`, gets `LITELLM_API_KEY`/`LITELLM_PROXY_URL`, runs `skill-benchmark` per selected skill (keep going past failures), and uploads the reports as an artifact. Set `n_attempts` from the `attempts` input with `--ek` or a per-run `evals/config.yml` in the temp copy; never write into the checkout. Job `publish`: `needs: run`, `contents: write`, **no LLM secrets**. It downloads the artifact, runs `collect-benchmarks`, commits to branch `benchmarks/<run_id>` with the bot identity, pushes, and prints a compare URL in the summary for a person to open the PR.
- [ ] **Step 5:** `pixi run -e ci test-scripts`, check-jsonschema on the workflow, `pixi run check-all`. Commit `ci: add manual benchmark workflow for trust pilot skills`.

### Task 10: First benchmark run

**Files:**
- Create: `plugins/<pilot>/skills/<skill>/BENCHMARK.md` × 16 (generated; never hand-edited, apart from an optional maintainer note under its own heading)

- [ ] **Step 1: Run one skill first.** After Task 9 merges, the maintainer dispatches `benchmark-skills.yml` with `skills=supply-chain-hardened-ci-cd`. Expected: a `benchmarks/<run_id>` branch with one `BENCHMARK.md`.
- [ ] **Step 2: Run all 16.** Dispatch with `skills` empty. For any skill reported INCONCLUSIVE or FAIL, keep the result as it is and optionally add a short note on why.
- [ ] **Step 3: A person opens the PR from the branch.** Required checks run. `pixi run -e ci python .github/scripts/skill_trust.py changed-plugins <last-tag>` lists neither pilot plugin because of this PR. Merge.

### Task 11: Release staging, signing and packing

**Files:**
- Modify: `.github/scripts/skill_trust.py` (+ tests), `pixi.toml` (pin `model-signing`)
- Create: `.github/workflows/release-sign.yml`

**Interfaces:**
- Produces:
  - `stage(root: Path, out: Path) -> list[Path]` copies each pilot skill dir to `out/<plugin>--<skill>/` and returns the staged dirs.
  - `pack(staged: Path, version: str, out: Path) -> Path` writes `out/<plugin>--<skill>-<version>.tar.gz`, with the archive root `<plugin>--<skill>/`. It raises `ValueError` if `skill.oms.sig` is missing.
  - CLI: `skill_trust.py stage --out DIR`, `skill_trust.py pack --staged DIR --version V --out DIR`.

- [ ] **Step 1: Pin `model-signing`.** Pin the current release, conda-forge if available, otherwise PyPI. Run `model_signing sign --help` and `model_signing verify sigstore --help` and record the exact flag spellings (underscore or hyphen) the version uses. Later steps use them as recorded.
- [ ] **Step 2: Write failing tests.**
  - `test_stage_copies_only_pilot`.
  - `test_pack_requires_signature` → `ValueError`.
  - `test_pack_layout`: archive members all start with `<plugin>--<skill>/`, and `skill.oms.sig` is included.
  - `test_signature_detects_tamper` (skip if `model_signing` isn't importable): sign a staged dir with `model_signing sign key` using a throwaway EC key generated in `tmp_path` (keyless needs OIDC). Verify passes. Edit a file → verify fails. Restore it and add a new file → verify fails (Review Focus 4).
- [ ] **Step 3: Implement `stage` and `pack`.** Tests pass.
- [ ] **Step 4: Write `release-sign.yml`.**
  - Trigger: `release: types: [published]`.
  - One job: `contents: write` (upload assets) and `id-token: write` (Sigstore), with no other secrets.
  - Check out the release tag. Then `stage`, then `model_signing sign sigstore` on each staged dir with `--signature <dir>/skill.oms.sig` (ambient GitHub OIDC credentials), then `pack`, then `gh release upload "$TAG" <archives>`.
  - Signing runs last; nothing writes into a staged dir after it.
- [ ] **Step 5:** check-jsonschema on the workflow, `pixi run check-all`. Commit `ci: sign pilot skills with Sigstore on release`.
- [ ] **Step 6: Dry-run before the first signed release.** Push a throwaway tag in a fork, or ask the maintainer how they want to test, and publish a release there. **Not on `uw-ssec/savvy`**: Zenodo archives every published release. Download an archive and verify it with the Task 12 command against the fork's identity. Expected: pass. Edit a file and verify again: fail.

### Task 12: Release process and user docs

**Files:**
- Modify: `.claude/skills/release/SKILL.md`, `docs/releasing.md`, `docs/trust-and-safety.md`, `CHANGELOG.md` (Unreleased)

- [ ] **Step 1: Update the `release` skill.** Stop building zips for `supply-chain-security` and `ai-research-workflows`; `release-sign.yml` attaches signed archives for them. Add a pre-release step: if a pilot skill changed since the last tag, dispatch `benchmark-skills.yml` for it and merge the results before tagging. Add a step to put each pilot skill's benchmark verdict, from its `BENCHMARK.md`, in the release notes.
- [ ] **Step 2: Update `docs/releasing.md`.** Add a "Signed skill archives" section: what `release-sign.yml` does, that it runs on publish, and how to confirm the assets appeared.
- [ ] **Step 3: Update `docs/trust-and-safety.md`.** Add a "Checking a skill before you install it" section covering:
  - where the skill card, `BENCHMARK.md` and eval set live;
  - how to read a benchmark verdict, including that FAIL and INCONCLUSIVE results are published as they are;
  - what the capability keys mean (the Task 5 wording);
  - the verify command as a template. Its `--identity` is `https://github.com/uw-ssec/savvy/.github/workflows/release-sign.yml@refs/tags/<TAG>` and its identity provider is `https://token.actions.githubusercontent.com`. Use the flag spellings recorded in Task 11 Step 1.
- [ ] **Step 4: Add a `CHANGELOG.md` Unreleased entry** for the pilot.
- [ ] **Step 5:** `pixi run check-all` and `pixi run -e ci links-check`. Commit `docs: document skill trust evidence and signed archives`.
