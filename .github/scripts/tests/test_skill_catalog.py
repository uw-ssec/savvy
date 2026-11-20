from pathlib import Path

import pytest
import yaml
from conftest import _load, workflow_step

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def sc():
    return _load("skill_catalog")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def skill(root, plugin, name, description, body="# Title\n\nDoes the thing well.\n"):
    write(root / plugin / "skills" / name / "SKILL.md",
          f"---\nname: {name}\ndescription: {description!r}\n---\n{body}")


@pytest.fixture
def repo(tmp_path):
    """A core plugin with a skill, a command and an agent; a community plugin with one skill."""
    skill(tmp_path, "plugins/alpha", "one", "Builds widgets. Use when the user asks about widgets or gadgets.")
    write(tmp_path / "plugins/alpha/commands/go.md", "---\ndescription: Run the thing. More text.\n---\nbody\n")
    write(tmp_path / "plugins/alpha/agents/helper.md", "---\nname: helper\ndescription: Helps out. Long tail.\n---\n")
    skill(tmp_path, "community-plugins/beta", "two", "Use when you need two. Triggers: do two, make two.")
    meta = {
        "tiers": {"Core": "Core plugins.", "Community": "Community plugins."},
        "plugins": {
            "alpha": {"tier": "Core", "maintainer": "@org/team",
                      "skills": {"one": {"example": "Build me a widget."}}},
            "beta": {"tier": "Community", "maintainer": "@someone",
                     "skills": {"two": {"example": "Make two.", "maintainer": "@other"}}},
        },
    }
    write(tmp_path / "docs/catalog.yml", yaml.safe_dump(meta, sort_keys=False))
    return tmp_path


def meta(root):
    return yaml.safe_load((root / "docs/catalog.yml").read_text())


def save(root, data):
    write(root / "docs/catalog.yml", yaml.safe_dump(data, sort_keys=False))


# --- description parsing ------------------------------------------------------

@pytest.mark.parametrize("description, expected", [
    ("Use when X. Triggers: plan X, design it, how should we build X.",
     "“plan X”, “design it”, “how should we build X”"),
    ('Use this skill when users ask to "a b", "c d", "e f", or mention Q. Generates scripts.',
     "“a b”, “c d”, “e f”"),
    # One or two quotes are examples inside the clause, not a trigger list.
    ('Designs IA. Use when users report "I can\'t find anything," or when sorting cards.',
     'When users report "I can\'t find anything," or when sorting cards'),
    ("Does a thing. Use when the user asks about Zarr, e.g. .zarr files.",
     "When the user asks about Zarr, e.g. .zarr files"),
])
def test_trigger_phrases(sc, description, expected):
    assert sc.trigger_phrases(description) == expected


def test_what_it_does_skips_trigger_and_not_for_sentences(sc):
    desc = "Use when the user works with pixi. Not for pure pip projects. Manages environments."
    assert sc.what_it_does(desc, "") == "Manages environments."


def test_what_it_does_falls_back_to_body_intro_then_clause(sc):
    desc = "Use when comparing approaches. Triggers: compare, benchmark."
    body = "# T\n\nAn OPTIONAL step — only use when unsure. Prototype two approaches.\n\n## Later\n\nIgnored text.\n"
    assert sc.what_it_does(desc, body) == "Prototype two approaches."
    # Intro is only a heading and a list: use the "Use when" clause.
    assert sc.what_it_does(desc, "# T\n## Steps\n1. Do it.\n") == "Comparing approaches."


# --- sync and check -----------------------------------------------------------

def test_sync_then_check_passes(sc, repo, capsys):
    assert sc.main(["sync", "--root", str(repo)]) == 0
    assert sc.main(["check", "--root", str(repo)]) == 0
    text = (repo / "docs/catalog.md").read_text()
    assert ("| Core | alpha | [`one`](../plugins/alpha/skills/one/SKILL.md) | Builds widgets. | "
            "When the user asks about widgets or gadgets | Build me a widget. | @org/team |") in text
    # Per-skill maintainer override, explicit trigger list, body fallback for "what it does".
    assert "| Community | beta | [`two`](../community-plugins/beta/skills/two/SKILL.md) | Does the thing well. | " \
           "“do two”, “make two” | Make two. | @other |" in text
    assert "- [`/alpha:go`](../plugins/alpha/commands/go.md): Run the thing." in text
    assert "- [`helper`](../plugins/alpha/agents/helper.md): Helps out." in text
    # Core comes before Community, following the order of `tiers`.
    assert text.index("## Core plugins") < text.index("## Community plugins")


def test_check_fails_when_output_is_stale(sc, repo, capsys):
    sc.main(["sync", "--root", str(repo)])
    skill(repo, "plugins/alpha", "one", "Builds better widgets. Use when widgets.")
    assert sc.main(["check", "--root", str(repo)]) == 1
    assert "out of date" in capsys.readouterr().err


def test_check_fails_on_missing_entries(sc, repo, capsys):
    skill(repo, "plugins/alpha", "new-skill", "Does new things. Use when new.")
    write(repo / "plugins/gamma/skills/x/SKILL.md", "---\nname: x\ndescription: X. Use when x.\n---\n")
    assert sc.main(["check", "--root", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "alpha/new-skill: example prompt is required" in err
    assert "plugin gamma (plugins/gamma) has no entry" in err


def test_check_fails_on_bad_tier_maintainer_and_stale_entries(sc, repo, capsys):
    data = meta(repo)
    data["plugins"]["alpha"]["tier"] = "Domain"
    del data["plugins"]["beta"]["maintainer"]
    data["plugins"]["beta"]["skills"]["gone"] = {"example": "x"}
    data["plugins"]["removed"] = {"tier": "Core", "maintainer": "@x"}
    save(repo, data)
    assert sc.main(["check", "--root", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "plugin alpha: tier 'Domain' is not one of ['Core', 'Community']" in err
    assert "plugin beta: maintainer is required" in err
    assert "beta/gone: no such skill" in err
    assert "plugin removed: no such plugin directory" in err


def test_unreleased_plugin_is_validated_but_left_off_the_page(sc, repo, capsys):
    data = meta(repo)
    data["plugins"]["beta"]["released"] = False
    save(repo, data)
    assert sc.main(["sync", "--root", str(repo)]) == 0
    text = (repo / "docs/catalog.md").read_text()
    assert "beta" not in text and "## Community plugins" not in text
    assert "1 skills, 1 commands, and 1 agents across 1 plugins" in text
    # Its metadata is still required, so it is ready to publish when released.
    del data["plugins"]["beta"]["skills"]["two"]
    save(repo, data)
    assert sc.main(["check", "--root", str(repo)]) == 1
    assert "beta/two: example prompt is required" in capsys.readouterr().err


def test_released_must_be_a_boolean(sc, repo, capsys):
    data = meta(repo)
    data["plugins"]["beta"]["released"] = "no"
    save(repo, data)
    assert sc.main(["check", "--root", str(repo)]) == 1
    assert "plugin beta: released must be true or false" in capsys.readouterr().err


def test_activates_false_flags_the_example(sc, repo, capsys):
    data = meta(repo)
    data["plugins"]["alpha"]["skills"]["one"]["activates"] = False
    save(repo, data)
    assert sc.main(["check", "--root", str(repo)]) == 1
    assert "activates: false needs the issue tracking the fix" in capsys.readouterr().err
    data["plugins"]["alpha"]["skills"]["one"]["issue"] = 42
    save(repo, data)
    assert sc.main(["sync", "--root", str(repo)]) == 0
    assert ("Build me a widget. *(Not yet reliable: in testing, Claude handled this without loading the skill. "
            "Tracked in [#42](https://github.com/uw-ssec/savvy/issues/42).)*") in (repo / "docs/catalog.md").read_text()
    data["plugins"]["alpha"]["skills"]["one"].update(activates="no", issue="#42")
    save(repo, data)
    assert sc.main(["check", "--root", str(repo)]) == 1
    err = capsys.readouterr().err
    assert "activates must be true or false" in err
    assert "issue must be an issue number" in err


def test_pipes_in_text_are_escaped(sc, repo):
    data = meta(repo)
    data["plugins"]["alpha"]["skills"]["one"]["example"] = "Use a | b"
    save(repo, data)
    sc.main(["sync", "--root", str(repo)])
    assert "Use a \\| b" in (repo / "docs/catalog.md").read_text()


# --- the real repository and workflow -------------------------------------------

def test_repository_catalog_is_current(sc):
    assert sc.main(["check", "--root", str(REPO)]) == 0


def test_validate_workflow_runs_catalog_check():
    assert "pixi run catalog-check" in workflow_step("validate-plugins.yml", "Check the skill catalog")
