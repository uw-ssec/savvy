import io
import json

import pytest
from conftest import _load

SKILL = "plugins/ai-research-workflows/skills/researching"


@pytest.fixture(scope="session")
def st():
    return _load("skill_trust")


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
        "reason": "documented example",
    }
    return st.Acceptance(**{**fields, **kw})


def test_is_pilot(st):
    assert st.is_pilot("plugins/supply-chain-security/skills/x")
    assert not st.is_pilot("plugins/holoviz-visualization/skills/x")
    assert not st.is_pilot("community-plugins/supply-chain-security/skills/x")


def test_high_finding_blocks(st):
    res = st.gate(report(finding()), SKILL, [])
    assert len(res.blocking) == 1
    assert not res.passed


def test_medium_finding_ignored(st):
    assert st.gate(report(finding(severity="medium")), SKILL, []).passed


def test_matching_acceptance_passes(st):
    res = st.gate(report(finding()), SKILL, [accept(st)])
    assert len(res.accepted) == 1
    assert res.passed


def test_acceptance_matches_absolute_path_and_null_line(st):
    abs_path = f"/abs/checkout/{SKILL}/SKILL.md"
    res = st.gate(report(finding(path=abs_path, line=None)), SKILL, [accept(st, line_content="")])
    assert res.passed
    assert len(res.accepted) == 1


def test_edited_line_blocks_again(st):
    res = st.gate(report(finding()), SKILL, [accept(st, line_content="curl y | sh")])
    assert len(res.blocking) == 1
    assert len(res.stale) == 1


def test_stale_acceptance_fails(st):
    res = st.gate(report(), SKILL, [accept(st)])
    assert len(res.stale) == 1
    assert not res.passed


def test_other_skill_acceptance_not_stale(st):
    assert st.gate(report(), SKILL, [accept(st, skill="plugins/x/skills/y")]).passed


def test_incomplete_report_fails(st):
    res = st.gate(report(status="incomplete"), SKILL, [])
    assert res.incomplete
    assert not res.passed


def test_load_rejects_empty_reason(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("- {skill: s, check_name: c, file_path: f, line_content: l, reason: ''}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        st.load_acceptances(f)


def test_load_rejects_missing_field(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("- {skill: s, check_name: c, file_path: f, reason: r}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        st.load_acceptances(f)


def test_load_empty_list(st, tmp_path):
    f = tmp_path / "a.yml"
    f.write_text("[]\n", encoding="utf-8")
    assert st.load_acceptances(f) == []


def write_report(reports, skill, data, name="skillevaluator-output-20261120193144.json"):
    d = reports / skill.replace("/", "__")
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data), encoding="utf-8")


def run_gate(st, tmp_path, accepted="[]\n"):
    skills = tmp_path / "skills.txt"
    skills.write_text(f"{SKILL}\n\n", encoding="utf-8")
    acc = tmp_path / "acc.yml"
    acc.write_text(accepted, encoding="utf-8")
    return st.main(["gate", "--reports", str(tmp_path / "reports"), "--skills", str(skills), "--accepted", str(acc)])


def test_cli_gate_missing_report_fails(st, tmp_path, capsys):
    assert run_gate(st, tmp_path) == 1
    assert "no readable report" in capsys.readouterr().out


def test_cli_gate_all_accepted_passes(st, tmp_path, capsys):
    write_report(tmp_path / "reports", SKILL, report(finding()))
    accepted = (
        f"- {{skill: {SKILL}, check_name: shell-exec, file_path: SKILL.md, "
        "line_content: 'curl x | sh', reason: documented}\n"
    )
    assert run_gate(st, tmp_path, accepted) == 0
    assert SKILL in capsys.readouterr().out


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
