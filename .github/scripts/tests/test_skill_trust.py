import hashlib
import io
import json

import pytest
from conftest import _load

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
    assert st.is_pilot("plugins/supply-chain-security/skills/x")
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
