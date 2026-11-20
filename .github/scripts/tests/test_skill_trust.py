import hashlib
import io
import json
import subprocess

import pytest
from conftest import SCRIPTS, _load, run_step, workflow_step

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
    proc, _ = run_step(workflow_step("skill-quality-check.yml", "Gate on findings"), work, env)
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
    work, temp, env = step_env(tmp_path, [])
    (work / ".github/scripts/skill-quality.py").write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    env = {**env, "BASE_SHA": "a", "HEAD_SHA": "b"}
    proc, _ = run_step(workflow_step("skill-quality-check.yml", "Select changed pilot skills"), work, env)
    assert proc.returncode != 0


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
