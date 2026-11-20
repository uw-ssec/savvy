import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml
from conftest import SCRIPTS, WORKFLOWS, _load, run_step, workflow_step

SKILL = "plugins/ai-research-workflows/skills/researching"


@pytest.fixture(scope="session")
def st():
    return _load("skill_trust")


CONTENT = b"curl x | sh\n"
DIGEST = hashlib.sha256(CONTENT).hexdigest()


@pytest.fixture
def root(tmp_path):
    """Repo root holding the flagged SKILL.md (and the prefix-collision twin)."""
    for d in (SKILL, SKILL + "-y"):
        (tmp_path / d).mkdir(parents=True)
        (tmp_path / d / "SKILL.md").write_bytes(CONTENT)
    return tmp_path


def finding(severity="high", check="shell-exec", path="SKILL.md", line="curl x | sh"):
    return {"severity": severity, "check_name": check, "file_path": path, "line_content": line}


def report(*findings, status="failed"):
    return {"overall_status": status, "results": [{"validator": "v", "findings": list(findings)}]}


def accept(st, **kw):
    fields = {
        "skill": SKILL,
        "check_name": "shell-exec",
        "file_path": "SKILL.md",
        "line_content": "curl x | sh",
        "file_sha256": DIGEST,
        "reason": "documented example",
    }
    return st.Acceptance(**{**fields, **kw})


def test_is_pilot(st):
    assert st.is_pilot("plugins/ai-research-workflows/skills/x")
    assert not st.is_pilot("plugins/supply-chain-security/skills/x")
    assert not st.is_pilot("plugins/holoviz-visualization/skills/x")
    assert not st.is_pilot("community-plugins/supply-chain-security/skills/x")


def test_high_finding_blocks(st, root):
    res = st.gate(report(finding()), SKILL, [])
    assert len(res.blocking) == 1
    assert not res.passed


def test_medium_finding_ignored(st):
    assert st.gate(report(finding(severity="medium")), SKILL, []).passed


def test_matching_acceptance_passes(st, root):
    res = st.gate(report(finding()), SKILL, [accept(st)], root)
    assert len(res.accepted) == 1
    assert res.passed


def test_acceptance_matches_absolute_path_and_null_line(st, root):
    abs_path = f"/abs/checkout/{SKILL}/SKILL.md"
    res = st.gate(report(finding(path=abs_path, line=None)), SKILL, [accept(st, line_content="")], root)
    assert res.passed
    assert len(res.accepted) == 1


def test_edited_line_blocks_again(st, root):
    res = st.gate(report(finding()), SKILL, [accept(st, line_content="curl y | sh")], root)
    assert len(res.blocking) == 1
    assert len(res.stale) == 1


def test_edit_after_snippet_invalidates_acceptance(st, root):
    # The scanner truncates line_content; text appended after the snippet must not stay accepted.
    (root / SKILL / "SKILL.md").write_bytes(CONTENT + b"more text after the snippet\n")
    res = st.gate(report(finding()), SKILL, [accept(st)], root)
    assert len(res.blocking) == 1
    assert len(res.stale) == 1
    assert not res.passed


def test_missing_file_invalidates_acceptance(st, root):
    (root / SKILL / "SKILL.md").unlink()
    res = st.gate(report(finding()), SKILL, [accept(st)], root)
    assert len(res.blocking) == 1
    assert len(res.stale) == 1


def test_stale_acceptance_fails(st, root):
    res = st.gate(report(), SKILL, [accept(st)], root)
    assert len(res.stale) == 1
    assert not res.passed


def test_other_skill_acceptance_not_stale(st, root):
    assert st.gate(report(), SKILL, [accept(st, skill="plugins/x/skills/y")], root).passed


def test_incomplete_report_fails(st):
    res = st.gate(report(status="incomplete"), SKILL, [])
    assert res.incomplete
    assert not res.passed


def test_failed_report_with_a_missing_scanner_fails(st, root):
    # SkillEvaluator reports `failed`, not `incomplete`, when any check fails
    # outright, even if another scanner never ran. An accepted finding must not
    # let that through.
    rep = {**report(finding()), "incomplete_scans": ["gitleaks"]}
    res = st.gate(rep, SKILL, [accept(st)], root)
    assert res.incomplete
    assert not res.passed


def test_result_level_missing_scanner_fails(st):
    rep = report()
    rep["results"].append({"validator": "secrets", "findings": [], "incomplete_scans": ["gitleaks"]})
    res = st.gate(rep, SKILL, [])
    assert res.incomplete
    assert not res.passed


def test_report_with_no_validator_results_fails(st):
    res = st.gate({"overall_status": "passed", "results": []}, SKILL, [])
    assert res.incomplete
    assert not res.passed


def test_load_rejects_empty_reason(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text(
        f"- {{skill: s, check_name: c, file_path: f, line_content: l, file_sha256: '{DIGEST}', reason: ''}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        st.load_acceptances(f)


def test_load_rejects_missing_field(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("- {skill: s, check_name: c, file_path: f, reason: r}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        st.load_acceptances(f)


def test_load_rejects_missing_digest(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("- {skill: s, check_name: c, file_path: f, line_content: l, reason: r}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="file_sha256"):
        st.load_acceptances(f)


@pytest.mark.parametrize("bad", ["abc", "G" * 64, DIGEST.upper(), DIGEST + "0"])
def test_load_rejects_bad_digest(st, tmp_path, bad):
    f = tmp_path / "a.yml"
    f.write_text(
        f"- {{skill: s, check_name: c, file_path: f, line_content: l, file_sha256: '{bad}', reason: r}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="file_sha256"):
        st.load_acceptances(f)


def test_load_empty_list(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("[]\n", encoding="utf-8")
    assert st.load_acceptances(f) == []


def write_report(reports, skill, data, name="skillevaluator-output-20261120193144.json"):
    d = reports / skill.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data), encoding="utf-8")


def run_gate(st, tmp_path, accepted="[]\n", root=None):
    skills = tmp_path / "skills.txt"
    skills.write_text(f"{SKILL}\n\n", encoding="utf-8")
    acc = tmp_path / "acc.yml"
    acc.write_text(accepted, encoding="utf-8")
    return st.main(["gate", "--reports", str(tmp_path / "reports"), "--skills", str(skills), "--accepted", str(acc), "--root", str(root or tmp_path)])


def test_cli_gate_missing_report_fails(st, tmp_path, capsys):
    assert run_gate(st, tmp_path) == 1
    assert "no readable report" in capsys.readouterr().out


def test_cli_gate_all_accepted_passes(st, tmp_path, root, capsys):
    write_report(tmp_path / "reports", SKILL, report(finding()))
    accepted = (
        f"- {{skill: {SKILL}, check_name: shell-exec, file_path: SKILL.md, "
        f"line_content: 'curl x | sh', file_sha256: '{DIGEST}', reason: documented}}\n"
    )
    assert run_gate(st, tmp_path, accepted) == 0
    out = capsys.readouterr().out
    assert f"| `{SKILL}` | 0 | 1 | 0 | ✅ pass |" in out


def test_cli_gate_blocking_fails(st, tmp_path):
    write_report(tmp_path / "reports", SKILL, report(finding()))
    assert run_gate(st, tmp_path) == 1


def test_cli_gate_uses_newest_report(st, tmp_path):
    write_report(tmp_path / "reports", SKILL, report(finding()), name="skillevaluator-output-20260101000000.json")
    write_report(tmp_path / "reports", SKILL, report(), name="skillevaluator-output-20261120193144.json")
    assert run_gate(st, tmp_path) == 0


def test_select_pilot_filters(st, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(f"{SKILL}\nplugins/holoviz-visualization/skills/x\n"))
    assert st.main(["select-pilot"]) == 0
    assert capsys.readouterr().out == SKILL + "\n"


def test_select_pilot_empty_stdin(st, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert st.main(["select-pilot"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "bad", [{}, {"error": "boom"}, {"overall_status": "failed"}, {"overall_status": "passed", "results": None}]
)
def test_malformed_report_fails_closed(st, bad):
    res = st.gate(bad, SKILL, [])
    assert res.incomplete
    assert not res.passed


def test_critical_finding_blocks(st):
    assert len(st.gate(report(finding(severity="critical")), SKILL, []).blocking) == 1


def test_path_normalisation_ignores_prefix_collision(st, root):
    # "-y/SKILL.md" is what a prefix-only match on the skill dir would wrongly produce.
    res = st.gate(report(finding(path=f"/abs/{SKILL}-y/SKILL.md")), SKILL, [accept(st, file_path="-y/SKILL.md")], root)
    assert len(res.blocking) == 1
    assert len(res.stale) == 1


def test_cli_gate_incomplete_report_fails(st, tmp_path, capsys):
    write_report(tmp_path / "reports", SKILL, report(status="incomplete"))
    assert run_gate(st, tmp_path) == 1
    assert "scan incomplete" in capsys.readouterr().out


def test_cli_gate_missing_accepted_file_fails(st, tmp_path, capsys):
    skills = tmp_path / "skills.txt"
    skills.write_text(f"{SKILL}\n", encoding="utf-8")
    missing = tmp_path / "nope.yml"
    assert st.main(["gate", "--reports", str(tmp_path), "--skills", str(skills), "--accepted", str(missing)]) == 1
    assert "cannot load accepted findings" in capsys.readouterr().err


# The scan and gate steps of the security-scan job in skill-quality-check.yml, run as the runner would.


def step_env(tmp_path, skills):
    work = tmp_path / "pr"
    (work / ".github/scripts").mkdir(parents=True)
    (work / ".github/scripts/skill_trust.py").write_text((SCRIPTS / "skill_trust.py").read_text(encoding="utf-8"))
    (work / ".github/skill-security-accepted.yml").write_text("[]\n", encoding="utf-8")
    temp = tmp_path / "runner-temp"
    temp.mkdir()
    (temp / "pilot.txt").write_text("".join(s + "\n" for s in skills), encoding="utf-8")
    env = {"RUNNER_TEMP": str(temp), "GITHUB_STEP_SUMMARY": str(temp / "step-summary.md")}
    return work, temp, env


def test_gate_step_with_no_pilot_skills_passes_and_says_so(tmp_path):
    work, temp, env = step_env(tmp_path, [])
    proc, _ = run_step(workflow_step("skill-quality-check.yml", "Gate on findings"), work, env, {"pixi": "exit 99\n"})
    assert proc.returncode == 0, proc.stderr
    assert "_no pilot skills changed_" in (temp / "step-summary.md").read_text(encoding="utf-8")


def test_scan_step_keeps_going_past_a_failing_scan(tmp_path):
    work, temp, env = step_env(tmp_path, [SKILL, "plugins/ai-research-workflows/skills/other"])
    stub = 'echo "$@" >> "$RUNNER_TEMP/calls.txt"\nexit 1\n'
    proc, _ = run_step(workflow_step("skill-quality-check.yml", "Run security scan"), work, env, {"pixi": stub})
    assert proc.returncode == 0, proc.stderr
    calls = (temp / "calls.txt").read_text(encoding="utf-8").splitlines()
    assert len(calls) == 2
    assert all("skill-security-scan" in c for c in calls)


def test_select_step_fails_when_skill_selection_crashes(tmp_path):
    # A real repo with a non-gate change, so `git diff` succeeds and the
    # crashing selector is what the step actually runs.
    work, temp, env = select_repo(tmp_path, "docs/unrelated.md")
    (work / ".github/scripts/skill-quality.py").write_text(
        "import os, pathlib, sys\n"
        "pathlib.Path(os.environ['RUNNER_TEMP'], 'selector-ran').touch()\n"
        "sys.exit(3)\n",
        encoding="utf-8",
    )
    proc, _ = run_step(workflow_step("skill-quality-check.yml", "Select changed pilot skills"), work, env, {"pixi": "cat\n"})
    assert (temp / "selector-ran").exists()
    assert proc.returncode != 0


ALL_PILOT = ["plugins/ai-research-workflows/skills/alpha", "plugins/ai-research-workflows/skills/beta"]
# Stub pixi: `list-pilot` prints every pilot skill, `select-pilot` passes stdin through.
SELECT_PIXI = (
    'echo "$@" >> "$RUNNER_TEMP/calls.txt"\n'
    'case "$*" in\n'
    f'  *list-pilot*) printf "%s\\n" {" ".join(ALL_PILOT)} ;;\n'
    "  *select-pilot*) cat ;;\n"
    "esac\n"
)


def select_repo(tmp_path, changed_path):
    work, temp, env = step_env(tmp_path, [])
    (work / ".github/scripts/skill-quality.py").write_text(
        'print("plugins/ai-research-workflows/skills/alpha")\n', encoding="utf-8"
    )
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "config", "commit.gpgsign", "false")
    _git(work, "add", "-f", ".github")
    _git(work, "commit", "-q", "-m", "base")
    base = _git(work, "rev-parse", "HEAD")
    target = work / changed_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("changed\n", encoding="utf-8")
    _git(work, "add", "-f", changed_path)
    _git(work, "commit", "-q", "-m", "change")
    return work, temp, {**env, "BASE_SHA": base, "HEAD_SHA": _git(work, "rev-parse", "HEAD")}


@pytest.mark.parametrize("path", [
    ".github/scripts/skill_trust.py",
    ".github/scripts/skill-quality.py",
    ".github/skill-security-accepted.yml",
    ".github/skillevaluator-policy.yml",
    ".github/workflows/skill-quality-check.yml",
    "pixi.toml",
    "pixi.lock",
])
def test_select_step_rescans_every_pilot_skill_when_a_gate_input_changes(tmp_path, path):
    work, temp, env = select_repo(tmp_path, path)
    proc, outputs = run_step(workflow_step("skill-quality-check.yml", "Select changed pilot skills"), work, env, {"pixi": SELECT_PIXI})
    assert proc.returncode == 0, proc.stderr
    assert (temp / "pilot.txt").read_text(encoding="utf-8").splitlines() == ALL_PILOT
    assert outputs["count"] == "2"


def test_codeowners_cover_every_gate_input():
    # Anything that decides what the scan runs, flags or waives needs code-owner review.
    script = workflow_step("skill-quality-check.yml", "Select changed pilot skills")
    gate_inputs = script.split('gate_inputs="', 1)[1].split('"', 1)[0].split()
    owned = {
        line.split()[0].lstrip("/")
        for line in (SCRIPTS.parent / "CODEOWNERS").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert set(gate_inputs) <= owned, set(gate_inputs) - owned


def test_select_step_keeps_changed_only_selection_otherwise(tmp_path):
    work, temp, env = select_repo(tmp_path, "docs/unrelated.md")
    proc, outputs = run_step(workflow_step("skill-quality-check.yml", "Select changed pilot skills"), work, env, {"pixi": SELECT_PIXI})
    assert proc.returncode == 0, proc.stderr
    assert (temp / "pilot.txt").read_text(encoding="utf-8").splitlines() == ["plugins/ai-research-workflows/skills/alpha"]
    assert outputs["count"] == "1"


def test_security_scan_steps_run_the_script_in_the_pixi_env():
    for name in ("Select changed pilot skills", "Gate on findings"):
        script = workflow_step("skill-quality-check.yml", name)
        assert "python3 .github/scripts/skill_trust.py" not in script
        assert "pixi run -e ci python .github/scripts/skill_trust.py" in script


GOOD_CAPS = {
    "capability-network": "read",
    "capability-shell": "runs-commands",
    "capability-file": "write",
    "capability-environment": "none",
    "capability-mcp": "none",
}


def test_capabilities_all_present_valid(st):
    assert st.check_capabilities({"name": "x", "metadata": dict(GOOD_CAPS)}) == []


def test_capability_missing_key(st):
    caps = {k: v for k, v in GOOD_CAPS.items() if k != "capability-mcp"}
    errors = st.check_capabilities({"metadata": caps})
    assert len(errors) == 1 and "capability-mcp" in errors[0]


def test_capability_missing_metadata(st):
    assert len(st.check_capabilities({"name": "x"})) == 5


def test_capability_bad_value(st):
    errors = st.check_capabilities({"metadata": {**GOOD_CAPS, "capability-shell": "yes"}})
    assert len(errors) == 1 and "capability-shell" in errors[0]


def test_capabilities_with_folded_description(st):
    import yaml

    text = (
        "---\nname: x\ndescription: >-\n  Use when a long folded\n  description wraps.\n"
        "metadata:\n  references: references/a.md\n"
        + "".join(f"  {k}: {v}\n" for k, v in GOOD_CAPS.items())
        + "---\n\n# X\n"
    )
    fm = yaml.safe_load(text.split("---\n")[1])
    assert all(isinstance(v, str) for v in fm["metadata"].values())
    assert st.check_capabilities(fm) == []


# --- evidence check: skill card + capabilities ---------------------------------


def card_text(sections, decorate=lambda s: s):
    return "# Card\n\n" + "".join(f"## {decorate(s)}\n\nText.\n\n" for s in sections)


def make_skill(root, name, sections=None, caps=GOOD_CAPS, plugin="ai-research-workflows", card=True):
    d = root / "plugins" / plugin / "skills" / name
    d.mkdir(parents=True)
    meta = "".join(f"  {k}: {v}\n" for k, v in (caps or {}).items())
    d.joinpath("SKILL.md").write_text(f"---\nname: {name}\ndescription: >-\n  Use when x.\nmetadata:\n{meta}---\n\n# X\n", encoding="utf-8")
    if card:
        d.joinpath("skill-card.md").write_text(card_text(sections or SECTIONS), encoding="utf-8")
    return d


SECTIONS = (
    "Owner",
    "License",
    "Use Case",
    "Deployment Geography",
    "Credentials",
    "Risks and Mitigations",
    "Output",
    "Version",
    "Ethics",
)


def test_card_sections_constant(st):
    assert st.SKILL_CARD_SECTIONS == SECTIONS


def test_card_missing_section(st, tmp_path):
    d = make_skill(tmp_path, "a", sections=[s for s in SECTIONS if s != "Ethics"])
    errors = st.check_card(d)
    assert len(errors) == 1 and "Ethics" in errors[0]


def test_card_complete(st, tmp_path):
    assert st.check_card(make_skill(tmp_path, "a")) == []


def test_card_headings_case_insensitive_and_decorated(st, tmp_path):
    d = make_skill(tmp_path, "a")
    d.joinpath("skill-card.md").write_text(card_text([s.upper() for s in SECTIONS], lambda s: s + ": <br>"), encoding="utf-8")
    assert st.check_card(d) == []


def test_card_h3_does_not_count(st, tmp_path):
    d = make_skill(tmp_path, "a")
    d.joinpath("skill-card.md").write_text(card_text(SECTIONS).replace("## Ethics", "### Ethics"), encoding="utf-8")
    assert any("Ethics" in e for e in st.check_card(d))


def test_card_missing_file(st, tmp_path):
    errors = st.check_card(make_skill(tmp_path, "a", card=False))
    assert len(errors) == 1 and "skill-card.md" in errors[0]


def test_check_skill_reports_capabilities_and_card(st, tmp_path):
    d = make_skill(tmp_path, "a", caps={}, card=False)
    errors = st.check_skill(d, require_evals=False)
    assert sum("capability-" in e for e in errors) == 5 and any("skill-card.md" in e for e in errors)


def test_check_skill_unreadable_frontmatter(st, tmp_path):
    d = make_skill(tmp_path, "a")
    d.joinpath("SKILL.md").write_text("# no frontmatter\n", encoding="utf-8")
    assert any("frontmatter" in e for e in st.check_skill(d, require_evals=False))


def test_check_skill_clean(st, tmp_path):
    assert st.check_skill(make_skill(tmp_path, "a"), require_evals=False) == []


def write_evals(d, name=None, cases=None, raw=None):
    name = name or d.name
    if cases is None:
        cases = [case(f"{name}-{i:03d}") for i in range(1, 6)] + [case(f"{name}-neg-001")]
    (d / "evals").mkdir(exist_ok=True)
    text = raw if raw is not None else json.dumps({"skill_name": name, "evals": cases})
    (d / "evals" / "evals.json").write_text(text, encoding="utf-8")


def case(id_, **kw):
    return {"id": id_, "prompt": "p", "expected_output": "o", "assertions": ["a"], **kw}


def test_evals_valid(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d)
    assert st.check_evals(d) == []


def test_evals_missing_file(st, tmp_path):
    assert any("evals.json" in e for e in st.check_evals(make_skill(tmp_path, "a")))


def test_evals_malformed_json(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, raw="{not json")
    assert any("evals.json" in e for e in st.check_evals(d))


def test_evals_no_negative(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case(f"a-{i:03d}") for i in range(1, 6)])
    assert any("neg" in e for e in st.check_evals(d))


def test_evals_too_few_positives(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case(f"a-{i:03d}") for i in range(1, 5)] + [case("a-neg-001")])
    assert any("at least 5" in e for e in st.check_evals(d))


def test_evals_wrong_skill_name(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, name="b", cases=[case(f"a-{i:03d}") for i in range(1, 6)] + [case("a-neg-001")])
    assert any("skill_name" in e for e in st.check_evals(d))


def test_evals_duplicate_id(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case(f"a-{i:03d}") for i in range(1, 6)] + [case("a-001"), case("a-neg-001")])
    assert any("duplicate" in e for e in st.check_evals(d))


@pytest.mark.parametrize("drop", ["prompt", "expected_output", "assertions"])
def test_evals_case_missing_field(st, tmp_path, drop):
    d = make_skill(tmp_path, "a")
    bad = case("a-001")
    del bad[drop]
    write_evals(d, cases=[bad] + [case(f"a-{i:03d}") for i in range(2, 6)] + [case("a-neg-001")])
    assert any(drop in e for e in st.check_evals(d))


def test_evals_empty_assertions(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case("a-001", assertions=[])] + [case(f"a-{i:03d}") for i in range(2, 6)] + [case("a-neg-001")])
    assert any("assertions" in e for e in st.check_evals(d))


@pytest.mark.parametrize(
    "field,value",
    [("prompt", "  "), ("expected_output", ""), ("prompt", 5), ("assertions", "one string"), ("assertions", ["ok", " "]), ("assertions", [1])],
)
def test_evals_rejects_blank_or_mistyped_fields(st, tmp_path, field, value):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case("a-001", **{field: value})] + [case(f"a-{i:03d}") for i in range(2, 6)] + [case("a-neg-001")])
    assert any(field in e for e in st.check_evals(d))


def test_evals_foreign_id(st, tmp_path):
    d = make_skill(tmp_path, "a")
    write_evals(d, cases=[case("zzz-001")] + [case(f"a-{i:03d}") for i in range(1, 6)] + [case("a-neg-001")])
    assert any("zzz-001" in e for e in st.check_evals(d))


def test_check_skill_requires_evals(st, tmp_path):
    d = make_skill(tmp_path, "a")
    assert any("evals.json" in e for e in st.check_skill(d))
    write_evals(d)
    assert st.check_skill(d) == []


def test_check_cli_reports_every_skill(st, tmp_path, capsys):
    make_skill(tmp_path, "good")
    make_skill(tmp_path, "broken", sections=[s for s in SECTIONS if s != "Ethics"])
    make_skill(tmp_path, "other-plugin-skill", plugin="not-in-pilot", card=False)
    assert st.main(["check", "--no-evals", "--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "broken" in err and "Ethics" in err
    assert "good" not in err and "other-plugin-skill" not in err


def test_check_cli_passes(st, tmp_path):
    make_skill(tmp_path, "good")
    assert st.main(["check", "--no-evals", "--root", str(tmp_path)]) == 0


def test_check_cli_no_skills_fails(st, tmp_path):
    assert st.main(["check", "--no-evals", "--root", str(tmp_path)]) == 1


# --- changed-plugins -------------------------------------------------------


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def grepo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    for d in ("plugins/p", "community-plugins/c"):
        (tmp_path / d / "skills/a").mkdir(parents=True)
        (tmp_path / d / "skills/a/SKILL.md").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _commit(repo, edits):
    base = _git(repo, "rev-parse", "HEAD")
    for path, text in edits.items():
        p = repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change")
    return base


@pytest.mark.parametrize("path", [
    "plugins/p/skills/a/evals/evals.json",
    "plugins/p/skills/a/evals/files/deep/x.md",
    "plugins/p/skills/a/BENCHMARK.md",
    "plugins/p/skills/a/skill-card.md",
])
def test_evidence_only_changes_are_not_plugin_changes(st, grepo, path):
    base = _commit(grepo, {path: "new\n"})
    assert st.changed_plugins(grepo, base) == []


@pytest.mark.parametrize("path", [
    "plugins/p/skills/a/SKILL.md",
    "plugins/p/skills/a/references/BENCHMARK.md",
    "plugins/p/skills/a/assets/skill-card.md",
    "plugins/p/skills/a/references/evals/x.md",
    "plugins/p/plugin.json",
    "plugins/p/README.md",
    "plugins/p/BENCHMARK.md",
])
def test_non_evidence_changes_count(st, grepo, path):
    base = _commit(grepo, {path: "new\n"})
    assert st.changed_plugins(grepo, base) == ["plugins/p"]


def test_evidence_plus_real_change_counts(st, grepo):
    base = _commit(grepo, {"plugins/p/skills/a/SKILL.md": "y\n", "plugins/p/skills/a/BENCHMARK.md": "b\n"})
    assert st.changed_plugins(grepo, base) == ["plugins/p"]


def test_changed_plugins_handles_non_ascii_paths(st, grepo):
    base = _commit(grepo, {"plugins/p/skills/a/références/été.md": "x\n"})
    assert st.changed_plugins(grepo, base) == ["plugins/p"]


def test_changed_plugins_sorted_across_both_roots_and_ignores_non_plugin_paths(st, grepo):
    base = _commit(grepo, {
        "community-plugins/c/skills/a/SKILL.md": "y\n",
        "plugins/p/skills/a/SKILL.md": "y\n",
        "docs/x.md": "d\n",
    })
    assert st.changed_plugins(grepo, base) == ["community-plugins/c", "plugins/p"]


def test_changed_plugins_cli(st, grepo, capsys):
    base = _commit(grepo, {"community-plugins/c/skills/a/SKILL.md": "y\n", "plugins/p/skills/a/SKILL.md": "y\n"})
    assert st.main(["changed-plugins", base, "--root", str(grepo)]) == 0
    assert capsys.readouterr().out == "community-plugins/c\nplugins/p\n"


def test_moving_a_file_across_plugins_marks_both(st, grepo):
    base = _git(grepo, "rev-parse", "HEAD")
    _git(grepo, "mv", "plugins/p/skills/a/SKILL.md", "community-plugins/c/skills/a/MOVED.md")
    _git(grepo, "commit", "-q", "-m", "move")
    assert st.changed_plugins(grepo, base) == ["community-plugins/c", "plugins/p"]


def test_deleting_a_file_marks_its_plugin(st, grepo):
    base = _git(grepo, "rev-parse", "HEAD")
    _git(grepo, "rm", "-q", "plugins/p/skills/a/SKILL.md")
    _git(grepo, "commit", "-q", "-m", "rm")
    assert st.changed_plugins(grepo, base) == ["plugins/p"]


def test_changed_plugins_bad_revision_exits_1_cleanly(st, grepo, capsys):
    assert st.main(["changed-plugins", "no-such-tag", "--root", str(grepo)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


SKILL_A = "plugins/ai-research-workflows/skills/alpha"
SKILL_B = "plugins/ai-research-workflows/skills/beta"


def test_collect_benchmarks_copies_and_lists_missing(st, tmp_path, capsys):
    root, reports = tmp_path / "repo", tmp_path / "reports"
    for skill in (SKILL_A, SKILL_B):
        (root / skill).mkdir(parents=True)
    (reports / st.report_name(SKILL_A)).mkdir(parents=True)
    (reports / st.report_name(SKILL_A) / "BENCHMARK.md").write_text("bench a\n", encoding="utf-8")
    code = st.main(["collect-benchmarks", "--reports", str(reports), "--root", str(root), "--skills", f"{SKILL_A},{SKILL_B}"])
    assert code == 0
    assert (root / SKILL_A / "BENCHMARK.md").read_text(encoding="utf-8") == "bench a\n"
    assert not (root / SKILL_B / "BENCHMARK.md").exists()
    out = capsys.readouterr().out
    assert f"updated: {SKILL_A}" in out
    assert f"missing: {SKILL_B}" in out


def test_collect_benchmarks_leaves_existing_file_when_report_missing(st, tmp_path):
    root = tmp_path / "repo"
    (root / SKILL_A).mkdir(parents=True)
    (root / SKILL_A / "BENCHMARK.md").write_text("old\n", encoding="utf-8")
    assert st.main(["collect-benchmarks", "--reports", str(tmp_path / "none"), "--root", str(root), "--skills", SKILL_A]) == 0
    assert (root / SKILL_A / "BENCHMARK.md").read_text(encoding="utf-8") == "old\n"


def test_collect_benchmarks_rejects_non_pilot_skill(st, tmp_path, capsys):
    assert st.main(["collect-benchmarks", "--reports", str(tmp_path), "--root", str(tmp_path), "--skills", "plugins/other/skills/x"]) == 1
    assert "not a pilot skill" in capsys.readouterr().err


def test_list_pilot_all_when_empty(st, tmp_path, capsys):
    for skill in (SKILL_B, SKILL_A):
        (tmp_path / skill).mkdir(parents=True)
    (tmp_path / "plugins/ai-research-workflows/skills/not-a-dir.txt").write_text("x", encoding="utf-8")
    assert st.main(["list-pilot", "--root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == f"{SKILL_A}\n{SKILL_B}\n"


def test_list_pilot_validates_given_skills(st, tmp_path, capsys):
    (tmp_path / SKILL_A).mkdir(parents=True)
    assert st.main(["list-pilot", "--root", str(tmp_path), "--skills", f" {SKILL_A}/ , {SKILL_A}"]) == 0
    assert capsys.readouterr().out == f"{SKILL_A}\n"


@pytest.mark.parametrize("bad", ["plugins/other/skills/x", f"{SKILL_A}/../../../../etc", "../x", SKILL_B])
def test_list_pilot_rejects_bad_skills(st, tmp_path, capsys, bad):
    (tmp_path / SKILL_A).mkdir(parents=True)
    assert st.main(["list-pilot", "--root", str(tmp_path), "--skills", f"{SKILL_A},{bad}"]) == 1
    assert "error:" in capsys.readouterr().err


def test_benchmark_env_pins_same_skillevaluator_as_ci():
    import tomllib

    from conftest import SCRIPTS

    feature = tomllib.loads((SCRIPTS.parents[1] / "pixi.toml").read_text(encoding="utf-8"))["feature"]
    ci = feature["ci"]["pypi-dependencies"]["skillevaluator"]
    bench = feature["benchmark"]["pypi-dependencies"]["skillevaluator"]
    assert (bench["git"], bench["rev"]) == (ci["git"], ci["rev"])


def test_scanners_env_installs_semgrep_from_a_linux_wheel():
    # Semgrep publishes only manylinux_2_34 wheels. If the scanners env's
    # declared glibc is older, the lock falls back to the sdist, and CI's
    # locked install rejects the wheel the sdist builds.
    lock = yaml.safe_load((SCRIPTS.parents[1] / "pixi.lock").read_text(encoding="utf-8"))
    # A platform with extra system requirements gets its own name (e.g.
    # linux-64-glibc-2-34); its `subdir` still says linux-64.
    linux_names = {p["name"] for p in lock["platforms"] if p.get("subdir", p["name"]) == "linux-64"}
    packages = lock["environments"]["scanners"]["packages"]
    linux = [entry for name in linux_names & packages.keys() for entry in packages[name]]
    semgrep = [entry["pypi"] for entry in linux if "pypi" in entry and "/semgrep-" in entry["pypi"]]
    assert semgrep and all(url.endswith(".whl") for url in semgrep), semgrep


def run_select(tmp_path, **env):
    script = workflow_step("benchmark-skills.yml", "Validate inputs and select skills")
    stubs = {"pixi": 'echo "plugins/ai-research-workflows/skills/alpha"\n'}
    base = {"SKILLS_INPUT": "", "MODEL": "ssec-claude-sonnet-5-5", "ATTEMPTS": "3"}
    return run_step(script, tmp_path, {**base, **env}, stubs)


def test_benchmark_select_step_accepts_defaults(tmp_path):
    proc, outputs = run_select(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert outputs["skills"] == "plugins/ai-research-workflows/skills/alpha"


@pytest.mark.parametrize("env", [{"ATTEMPTS": "0"}, {"ATTEMPTS": "3; id"}, {"MODEL": "m --x"}, {"MODEL": "$(id)"}])
def test_benchmark_select_step_rejects_bad_inputs(tmp_path, env):
    proc, _ = run_select(tmp_path, **env)
    assert proc.returncode == 1
    assert "::error::" in proc.stdout


def key_check(tmp_path, report_text, key="sk-secret-123"):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "BENCHMARK.md").write_text(report_text, encoding="utf-8")
    script = workflow_step("benchmark-skills.yml", "Check reports for the API key")
    proc, _ = run_step(script, tmp_path, {"RUNNER_TEMP": str(tmp_path), "ANTHROPIC_API_KEY": key})
    return proc


def test_benchmark_key_check_passes_clean_reports(tmp_path):
    assert key_check(tmp_path, "all good\n").returncode == 0


def test_benchmark_key_check_fails_when_key_is_in_a_report_and_never_echoes_it(tmp_path):
    proc = key_check(tmp_path, "leaked sk-secret-123 here\n")
    assert proc.returncode != 0
    assert "API key found" in proc.stdout
    assert "sk-secret-123" not in proc.stdout + proc.stderr


def test_benchmark_key_check_fails_on_empty_key(tmp_path):
    assert key_check(tmp_path, "anything\n", key="").returncode != 0


def test_benchmark_upload_and_publish_conditions():
    doc = yaml.safe_load((WORKFLOWS / "benchmark-skills.yml").read_text(encoding="utf-8"))
    steps = {step.get("name"): step for step in doc["jobs"]["run"]["steps"]}
    names = [step.get("name") for step in doc["jobs"]["run"]["steps"]]
    assert names.index("Check reports for the API key") < names.index("Upload reports")
    assert "always()" in steps["Upload reports"]["if"]
    assert "cancelled" not in steps["Upload reports"]["if"]
    assert "keycheck" in steps["Upload reports"]["if"]
    assert doc["jobs"]["publish"]["if"] == "${{ needs.run.result == 'success' }}"


# --- release staging and packing ---------------------------------------------

PILOT_SKILL = "plugins/ai-research-workflows/skills/alpha"


@pytest.fixture
def release_root(tmp_path):
    """Repo root with two pilot skills, one non-pilot plugin skill, and a nested skill file."""
    root = tmp_path / "repo"
    for rel, body in {
        f"{PILOT_SKILL}/SKILL.md": "alpha\n",
        f"{PILOT_SKILL}/references/notes.md": "notes\n",
        f"{PILOT_SKILL}/.gitignore": "x\n",
        "plugins/ai-research-workflows/skills/beta/SKILL.md": "beta\n",
        "plugins/other/skills/gamma/SKILL.md": "gamma\n",
    }.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def test_stage_copies_only_pilot(st, release_root, tmp_path):
    out = tmp_path / "staged"
    staged = st.stage(release_root, out)
    assert sorted(p.name for p in staged) == ["ai-research-workflows--alpha", "ai-research-workflows--beta"]
    assert sorted(p.name for p in out.iterdir()) == [p.name for p in sorted(staged)]
    alpha = out / "ai-research-workflows--alpha"
    assert (alpha / "SKILL.md").read_text(encoding="utf-8") == "alpha\n"
    assert (alpha / "references" / "notes.md").read_text(encoding="utf-8") == "notes\n"
    assert (alpha / ".gitignore").exists()


def test_stage_rejects_symlinks(st, release_root, tmp_path):
    (release_root / PILOT_SKILL / "link.md").symlink_to(release_root / "plugins/other/skills/gamma/SKILL.md")
    with pytest.raises(ValueError, match="symlink"):
        st.stage(release_root, tmp_path / "staged")


def staged_skill(st, release_root, tmp_path, sign=True):
    staged = st.stage(release_root, tmp_path / "staged")
    alpha = next(p for p in staged if p.name.endswith("--alpha"))
    if sign:
        (alpha / "skill.oms.sig").write_text("sig\n", encoding="utf-8")
    return alpha


def test_pack_requires_signature(st, release_root, tmp_path):
    alpha = staged_skill(st, release_root, tmp_path, sign=False)
    with pytest.raises(ValueError, match="skill.oms.sig"):
        st.pack(alpha, "26.11.0", tmp_path / "dist")


def test_pack_layout(st, release_root, tmp_path):
    alpha = staged_skill(st, release_root, tmp_path)
    archive = st.pack(alpha, "26.11.0", tmp_path / "dist")
    assert archive == tmp_path / "dist" / "ai-research-workflows--alpha-26.11.0.tar.gz"
    with tarfile.open(archive) as tar:
        names = tar.getnames()
        assert all(n == "ai-research-workflows--alpha" or n.startswith("ai-research-workflows--alpha/") for n in names)
        assert "ai-research-workflows--alpha/skill.oms.sig" in names
        assert "ai-research-workflows--alpha/references/notes.md" in names
        assert all(m.uid == 0 and m.gid == 0 and m.mtime == 0 for m in tar.getmembers())


def test_pack_is_deterministic(st, release_root, tmp_path):
    alpha = staged_skill(st, release_root, tmp_path)
    first = st.pack(alpha, "26.11.0", tmp_path / "d1").read_bytes()
    second = st.pack(alpha, "26.11.0", tmp_path / "d2").read_bytes()
    assert first == second


@pytest.mark.parametrize("version", ["26.11.0", "26.4.1", "27.12.10"])
def test_pack_accepts_calendar_versions(st, release_root, tmp_path, version):
    alpha = staged_skill(st, release_root, tmp_path)
    assert st.pack(alpha, version, tmp_path / "dist").name.endswith(f"-{version}.tar.gz")


@pytest.mark.parametrize(
    "version", ["", "v26.11.0", "26.04.0", "../26.11.0", "26.11.0/x", "26.13.0", "26.11", "26.11.0-rc1"]
)
def test_pack_rejects_bad_versions(st, release_root, tmp_path, version):
    alpha = staged_skill(st, release_root, tmp_path)
    with pytest.raises(ValueError, match="version"):
        st.pack(alpha, version, tmp_path / "dist")


def test_pack_rejects_symlink_added_after_staging(st, release_root, tmp_path):
    alpha = staged_skill(st, release_root, tmp_path)
    (alpha / "link.md").symlink_to(release_root / "plugins/other/skills/gamma/SKILL.md")
    with pytest.raises(ValueError, match="symlink"):
        st.pack(alpha, "26.11.0", tmp_path / "dist")


def test_check_version_cli(st, capsys):
    assert st.main(["check-version", "26.11.0"]) == 0
    assert st.main(["check-version", "26.11.0-rc1"]) == 1
    assert st.main(["check-version", "v26.11.0"]) == 1
    assert "error" in capsys.readouterr().err


def test_signing_env_pins_same_model_signing_as_ci():
    import tomllib

    feature = tomllib.loads((SCRIPTS.parents[1] / "pixi.toml").read_text(encoding="utf-8"))["feature"]
    assert feature["signing"]["pypi-dependencies"]["model-signing"] == feature["ci"]["pypi-dependencies"]["model-signing"]
    assert feature["signing"]["dependencies"]["pyopenssl"] == feature["ci"]["dependencies"]["pyopenssl"]


def test_release_workflow_is_hardened():
    doc = yaml.safe_load((WORKFLOWS / "release-sign.yml").read_text(encoding="utf-8"))
    job = doc["jobs"]["sign"]
    setup = next(step for step in job["steps"] if "setup-pixi" in step.get("uses", ""))
    assert setup["with"]["cache"] is False
    assert setup["with"]["environments"] == "signing"
    assert "-e ci" not in yaml.safe_dump(job)
    assert doc["concurrency"]["cancel-in-progress"] is False
    steps = [step.get("name") for step in job["steps"]]
    assert steps.index("Check version") < steps.index("Stage pilot skills")


def model_signing_cmd():
    return shutil.which("model_signing") or str(Path(sys.executable).parent / "model_signing")


def test_signature_detects_tamper(st, release_root, tmp_path):
    pytest.importorskip("model_signing")
    ec = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ec")
    ser = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    key = ec.generate_private_key(ec.SECP256R1())
    private = tmp_path / "priv.pem"
    public = tmp_path / "pub.pem"
    private.write_bytes(key.private_bytes(ser.Encoding.PEM, ser.PrivateFormat.PKCS8, ser.NoEncryption()))
    public.write_bytes(key.public_key().public_bytes(ser.Encoding.PEM, ser.PublicFormat.SubjectPublicKeyInfo))

    alpha = staged_skill(st, release_root, tmp_path, sign=False)
    sig = alpha / "skill.oms.sig"
    common = ["--signature", str(sig), "--no-ignore-git-paths"]

    def run(*args):
        return subprocess.run([model_signing_cmd(), *args], capture_output=True, text=True)

    signed = run("sign", "key", str(alpha), *common, "--private_key", str(private))
    assert signed.returncode == 0, signed.stderr

    def verify():
        return run("verify", "key", str(alpha), *common, "--public_key", str(public))

    assert verify().returncode == 0, "untouched skill must verify"
    skill_md = alpha / "SKILL.md"
    skill_md.write_text("tampered\n", encoding="utf-8")
    assert verify().returncode != 0, "edited file must fail"
    skill_md.write_text("alpha\n", encoding="utf-8")
    assert verify().returncode == 0, "restored file must verify again"
    (alpha / "extra.md").write_text("added\n", encoding="utf-8")
    assert verify().returncode != 0, "added file must fail"
    (alpha / "extra.md").unlink()
    (alpha / ".gitignore").write_text("changed\n", encoding="utf-8")
    assert verify().returncode != 0, "edited dotfile must fail (not ignored)"


def test_stage_sign_pack_end_to_end_through_the_cli(st, release_root, tmp_path):
    pytest.importorskip("model_signing")
    ec = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ec")
    ser = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    key = ec.generate_private_key(ec.SECP256R1())
    private = tmp_path / "priv.pem"
    private.write_bytes(key.private_bytes(ser.Encoding.PEM, ser.PrivateFormat.PKCS8, ser.NoEncryption()))

    staged = tmp_path / "staged"
    assert st.main(["stage", "--root", str(release_root), "--out", str(staged)]) == 0
    dirs = sorted(p for p in staged.iterdir() if p.is_dir())
    assert [p.name for p in dirs] == ["ai-research-workflows--alpha", "ai-research-workflows--beta"]
    for d in dirs:
        signed = subprocess.run(
            [model_signing_cmd(), "sign", "key", str(d), "--signature", str(d / "skill.oms.sig"),
             "--no-ignore-git-paths", "--private_key", str(private)],
            capture_output=True, text=True,
        )
        assert signed.returncode == 0, signed.stderr
    dist = tmp_path / "dist"
    assert st.main(["pack", "--staged", str(staged), "--version", "26.11.0", "--out", str(dist)]) == 0
    assert sorted(p.name for p in dist.iterdir()) == [
        "ai-research-workflows--alpha-26.11.0.tar.gz",
        "ai-research-workflows--beta-26.11.0.tar.gz",
    ]
    with tarfile.open(dist / "ai-research-workflows--alpha-26.11.0.tar.gz") as tar:
        assert "ai-research-workflows--alpha/skill.oms.sig" in tar.getnames()
