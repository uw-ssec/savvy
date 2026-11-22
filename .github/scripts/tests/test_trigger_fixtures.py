"""Check evals/catalog-triggers/fixtures/: one well-formed trigger fixture per skill."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "evals/catalog-triggers/fixtures"
SKILLS = sorted(f"{p.parts[-4]}/{p.parts[-2]}" for p in
                [*ROOT.glob("plugins/*/skills/*/SKILL.md"), *ROOT.glob("community-plugins/*/skills/*/SKILL.md")])
COMMANDS = sorted(f"{p.parts[-3]}:{p.stem}" for p in
                  [*ROOT.glob("plugins/*/commands/*.md"), *ROOT.glob("community-plugins/*/commands/*.md")])
EXPECT = {"obvious": "fire", "tired": "fire", "neighbor": "no-fire", "negative": "no-fire"}


def load(skill: str) -> dict:
    return json.loads((FIXTURES / f"{skill}.json").read_text(encoding="utf-8"))


def test_every_skill_has_a_fixture_and_no_stray_files():
    files = sorted(str(p.relative_to(FIXTURES).with_suffix("")) for p in FIXTURES.glob("*/*.json"))
    assert files == SKILLS


@pytest.mark.parametrize("skill", SKILLS)
def test_fixture_is_well_formed(skill):
    data = load(skill)
    assert data["skill"] == skill
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    name = skill.split("/")[1]
    for c in cases:
        assert set(c) <= {"id", "kind", "expect", "owner", "prompt"}, c["id"]
        assert c["expect"] == EXPECT[c["kind"]], c["id"]
        assert c["prompt"].strip() and len(c["prompt"]) <= 600, c["id"]
        # A hyphenated name only shows up in a prompt by copying it; a one-word name such as
        # "researching" is ordinary English, so it's left to review.
        if "-" in name:
            assert not re.search(rf"\b{re.escape(name)}\b", c["prompt"], re.I), f"{c['id']} names the skill"
        if c["kind"] == "neighbor":
            assert c["owner"] in SKILLS or c["owner"] in COMMANDS, f"{c['id']}: unknown owner {c['owner']!r}"
            assert c["owner"] != skill, c["id"]
            if ":" in c["owner"]:
                # A command that uses the target skill can't own a request the skill must not take.
                plugin, command = c["owner"].split(":")
                body = next(ROOT.glob(f"*plugins/{plugin}/commands/{command}.md")).read_text(encoding="utf-8")
                target_plugin = skill.split("/")[0]
                assert not re.search(rf"`(?:{re.escape(target_plugin)}:)?{re.escape(name)}`", body), \
                    f"{c['id']}: {c['owner']} uses `{name}` itself"
        elif c["kind"] == "negative":
            assert c.get("owner") is None, c["id"]
        else:
            assert "owner" not in c, c["id"]
    prompts = [" ".join(c["prompt"].lower().split()) for c in cases]
    assert len(prompts) == len(set(prompts)), "duplicate prompt"
    kinds = [c["kind"] for c in cases]
    assert kinds.count("obvious") + kinds.count("tired") >= 3 and "tired" in kinds and "obvious" in kinds
    assert kinds.count("neighbor") + kinds.count("negative") >= 2 and "neighbor" in kinds


def trigger_test():
    import importlib.util
    spec = importlib.util.spec_from_file_location("trigger_test", ROOT / "evals/catalog-triggers/trigger_test.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_aggregate_applies_threshold_per_case_and_all_cases_per_skill():
    from fractions import Fraction
    tt = trigger_test()

    def r(skill, case, ok, invoked):
        return {"plugin": "p", "skill": skill, "case": case, "kind": "obvious", "expect": "fire",
                "pass": ok, "invoked": invoked}
    results = [r("a", "c1", True, "p:a"), r("a", "c1", True, "p:a"), r("a", "c1", False, None),
               r("b", "c1", True, "p:b"), r("b", "c1", False, None), r("b", "c1", False, "p:x")]
    skills = tt.aggregate(results, Fraction(2, 3))
    assert skills["p/a"]["pass"] and skills["p/a"]["cases"]["c1"]["passes"] == 2
    assert not skills["p/b"]["pass"] and skills["p/b"]["cases"]["c1"]["invoked"] == ["p:b", None, "p:x"]


def test_aggregate_leaves_failed_runs_out_and_never_passes_a_case_without_valid_runs():
    from fractions import Fraction
    tt = trigger_test()
    base = {"plugin": "p", "kind": "obvious", "expect": "fire", "invoked": None}
    results = [{**base, "skill": "a", "case": "c1", "pass": True, "error": None},
               {**base, "skill": "a", "case": "c1", "pass": None, "error": "no result event"},
               {**base, "skill": "b", "case": "c1", "pass": None, "error": "API Error: 401"}]
    skills = tt.aggregate(results, Fraction(2, 3))
    assert skills["p/a"]["pass"] and skills["p/a"]["cases"]["c1"]["runs"] == 1
    assert skills["p/a"]["cases"]["c1"]["errors"] == 1
    assert not skills["p/b"]["pass"] and skills["p/b"]["cases"]["c1"]["runs"] == 0


def test_runner_rejects_empty_or_unknown_selections(capsys):
    tt = trigger_test()
    for argv in (["--fixtures", "--repeats", "0"], ["--fixtures", "nope/nothing"]):
        with pytest.raises(SystemExit) as e:
            tt.main(argv)
        assert e.value.code == 2
