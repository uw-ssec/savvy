#!/usr/bin/env python3
"""Generate docs/catalog.md, the one-page skill catalog, and keep it in sync.

Usage (through pixi: `pixi run catalog-sync`, `catalog-check`):
    skill_catalog.py sync    # rewrite docs/catalog.md
    skill_catalog.py check   # fail if docs/catalog.md is stale or catalog.yml is incomplete (CI runs this)

Sources:

- ``<plugin>/skills/<skill>/SKILL.md`` frontmatter: the skill name and the
  ``description`` that Claude reads to decide when to activate the skill. The
  "What it does" and "Trigger phrases" columns are both cut from it, so the
  catalog can't promise a trigger the skill doesn't declare.
- ``<plugin>/commands/*.md`` and ``<plugin>/agents/*.md`` frontmatter.
- ``docs/catalog.yml``: what the frontmatter doesn't carry. Each plugin's tier
  and maintainer, and an example prompt for every skill.

How the description is split:

- Trigger phrases are, in order of preference, an explicit ``Triggers:`` /
  ``Trigger phrases:`` list, the quoted phrases in the description, or the
  "Use when ..." clause.
- What it does is the first sentence that isn't a trigger sentence. A
  description made only of trigger sentences falls back to the first sentence
  of the SKILL.md body.

Needs PyYAML.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PARENTS = ("plugins", "community-plugins")
METADATA = Path("docs/catalog.yml")
OUTPUT = Path("docs/catalog.md")
# Appended to an example prompt marked `activates: false` in catalog.yml.
ISSUES = "https://github.com/uw-ssec/savvy/issues"
NOT_ACTIVATED = ("*(Not yet reliable: in testing, Claude handled this without loading the skill. "
                 "Tracked in [#{issue}]({url}).)*")

TRIGGER_LIST = re.compile(r"\bTrigger(?:s| phrases):\s*(.+?)(?:\.\s*$|\.\s+(?=[A-Z])|$)", re.S)
QUOTED = re.compile(r"\"([^\"]+)\"")
USE_WHEN = re.compile(r"^Use (?:this skill )?when\s+", re.I)
# A sentence ends at . ! or ? followed by whitespace and a capital letter, so
# "e.g. pixi", ".zarr" and "Nguyen et al. (2023)" don't split.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"])")


def frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    _, fm, body = text.split("---", 2)
    return yaml.safe_load(fm) or {}, body


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(" ".join(text.split())) if s.strip()]


def is_trigger_sentence(s: str) -> bool:
    """Sentences that say when to use a skill (or when not to) rather than what it does."""
    return bool(USE_WHEN.match(s) or re.match(r"(?:Trigger(?:s| phrases):|Not for\b)", s)
                or re.search(r"\buse when\b", s, re.I))


def use_when_clause(description: str) -> str:
    for s in sentences(description):
        if USE_WHEN.match(s):
            return USE_WHEN.sub("", s).rstrip(".")
    return ""


def trigger_phrases(description: str) -> str:
    flat = " ".join(description.split())
    if m := TRIGGER_LIST.search(flat):
        items = [p.strip().rstrip(".") for p in m.group(1).split(",") if p.strip()]
        return ", ".join(f"“{p}”" for p in items)
    # A run of quoted phrases is a trigger list; one or two quotes are usually
    # examples inside a "Use when" clause, which is the better source then.
    quoted = QUOTED.findall(flat)
    if len(quoted) >= 3:
        return ", ".join(f"“{p}”" for p in quoted)
    if clause := use_when_clause(flat):
        return f"When {clause}"
    return ""


LIST_ITEM = re.compile(r"^(?:[-*+]\s|\d+[.)]\s)")


def what_it_does(description: str, body: str) -> str:
    # 1. The first description sentence that isn't about when to use the skill.
    for s in sentences(description):
        if not is_trigger_sentence(s):
            return s
    # 2. The description is all trigger text: the first prose sentence of the
    #    body's intro (the text before its first "##" section).
    intro = re.split(r"^##\s", body, maxsplit=1, flags=re.M)[0].replace("**", "")
    for para in re.split(r"\n\s*\n", intro):
        para = para.strip()
        if not para or para.startswith(("#", "```", "|", ">", "<")) or LIST_ITEM.match(para):
            continue
        for s in sentences(para):
            if not is_trigger_sentence(s):
                return s
    # 3. No prose intro either: say what it's for, from the "Use when" clause.
    clause = use_when_clause(description)
    return clause[:1].upper() + clause[1:] + "." if clause else ""


def first_sentence(text: str) -> str:
    s = sentences(text)
    return s[0] if s else ""


def cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def plugin_dirs(root: Path) -> list[Path]:
    return sorted(d for parent in PLUGIN_PARENTS if (root / parent).is_dir()
                  for d in (root / parent).iterdir() if d.is_dir())


def anchor(title: str) -> str:
    """GitHub's heading anchor: lowercase, drop punctuation, spaces to hyphens."""
    return re.sub(r"[^a-z0-9 _-]", "", title.lower()).replace(" ", "-")


# --- loading and validation --------------------------------------------------

def load(root: Path) -> tuple[dict, list[dict], list[str]]:
    """Return (metadata, plugins, errors). Each plugin dict has everything the page needs."""
    errors: list[str] = []
    meta_path = root / METADATA
    if not meta_path.is_file():
        return {}, [], [f"{METADATA}: missing"]
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
    tiers = meta.get("tiers") or {}
    meta_plugins = meta.get("plugins") or {}

    plugins = []
    seen = set()
    for pdir in plugin_dirs(root):
        name = pdir.name
        seen.add(name)
        rel = pdir.relative_to(root).as_posix()
        pmeta = meta_plugins.get(name)
        if not isinstance(pmeta, dict):
            errors.append(f"{METADATA}: plugin {name} ({rel}) has no entry")
            continue
        tier = pmeta.get("tier")
        if tier not in tiers:
            errors.append(f"{METADATA}: plugin {name}: tier {tier!r} is not one of {list(tiers)}")
        maintainer = pmeta.get("maintainer")
        if not maintainer:
            errors.append(f"{METADATA}: plugin {name}: maintainer is required")
        skill_meta = pmeta.get("skills") or {}

        skills = []
        for skill_md in sorted(pdir.glob("skills/*/SKILL.md")):
            sname = skill_md.parent.name
            fm, body = frontmatter(skill_md)
            desc = fm.get("description") or ""
            smeta = skill_meta.get(sname) or {}
            example = (smeta.get("example") or "").strip()
            if not example:
                errors.append(f"{METADATA}: {name}/{sname}: example prompt is required")
            activates = smeta.get("activates", True)
            if not isinstance(activates, bool):
                errors.append(f"{METADATA}: {name}/{sname}: activates must be true or false")
            issue = smeta.get("issue")
            if issue is not None and not (isinstance(issue, int) and issue > 0):
                errors.append(f"{METADATA}: {name}/{sname}: issue must be an issue number")
            if activates is False and issue is None:
                errors.append(f"{METADATA}: {name}/{sname}: activates: false needs the issue tracking the fix")
            note = ""
            if activates is False:
                note = f" {NOT_ACTIVATED.format(issue=issue, url=f'{ISSUES}/{issue}')}"
            row = {
                "name": sname,
                "path": skill_md.relative_to(root).as_posix(),
                "does": what_it_does(desc, body),
                "triggers": trigger_phrases(desc),
                "example": example + note,
                "maintainer": smeta.get("maintainer") or maintainer,
            }
            for col in ("does", "triggers"):
                if not row[col]:
                    errors.append(f"{row['path']}: could not derive '{col}' from the description")
            skills.append(row)
        for stale in sorted(set(skill_meta) - {s["name"] for s in skills}):
            errors.append(f"{METADATA}: {name}/{stale}: no such skill (remove the entry)")

        def listing(sub: str) -> list[dict]:
            out = []
            for f in sorted(pdir.glob(f"{sub}/*.md")):
                fm, _ = frontmatter(f)
                out.append({"name": fm.get("name") or f.stem,
                            "path": f.relative_to(root).as_posix(),
                            "description": first_sentence(fm.get("description") or "")})
            return out

        plugins.append({"name": name, "path": rel, "tier": tier, "maintainer": maintainer,
                        "skills": skills, "commands": listing("commands"), "agents": listing("agents")})

    for stale in sorted(set(meta_plugins) - seen):
        errors.append(f"{METADATA}: plugin {stale}: no such plugin directory (remove the entry)")
    return meta, plugins, errors


# --- rendering ----------------------------------------------------------------

def render(meta: dict, plugins: list[dict]) -> str:
    tiers = meta.get("tiers") or {}
    n_skills = sum(len(p["skills"]) for p in plugins)
    n_cmds = sum(len(p["commands"]) for p in plugins)
    n_agents = sum(len(p["agents"]) for p in plugins)

    out = [
        "<!-- Generated by .github/scripts/skill_catalog.py from SKILL.md frontmatter and",
        "     docs/catalog.yml. Don't edit by hand: edit those, then run `pixi run catalog-sync`. -->",
        "",
        "# Skill catalog",
        "",
        f"Every skill, command, and agent in this repository: {n_skills} skills, "
        f"{n_cmds} commands, and {n_agents} agents across {len(plugins)} plugins.",
        "",
        "Skills activate on their own. Claude reads each skill's `description` and loads the skill when",
        "your request matches it, so you don't call a skill by name. The **Trigger phrases** column is",
        "taken from that description: phrase a request along those lines, or start from the",
        "**Example prompt**. Commands and agents are invoked differently; see the short list under each plugin.",
        "",
        "Each example prompt was run in Claude Code with these plugins installed. Where it didn't load the",
        "skill, the row says so: the skill still works when Claude loads it, but its description needs",
        "work before it triggers reliably. Mentioning the skill by name (\"use the ux-writing skill to ...\") works in the meantime.",
        "",
        "To report a problem with a skill, open an issue and mention its maintainer.",
        "",
        "## Tiers",
        "",
        "| Tier | What it means |",
        "| --- | --- |",
    ]
    out += [f"| {cell(t)} | {cell(d)} |" for t, d in tiers.items()]
    out += ["", "## Index", "", "| Tier | Plugin | Skills | Commands | Agents | Maintainer |",
            "| --- | --- | ---: | ---: | ---: | --- |"]
    ordered = [p for t in tiers for p in plugins if p["tier"] == t]
    for p in ordered:
        out.append(f"| {p['tier']} | [{p['name']}](#{anchor(p['name'])}) | {len(p['skills'])} | "
                   f"{len(p['commands'])} | {len(p['agents'])} | {cell(p['maintainer'])} |")

    for tier in tiers:
        out += ["", f"## {tier} plugins"]
        for p in (p for p in ordered if p["tier"] == tier):
            out += ["", f"### {p['name']}", "",
                    f"Source: [`{p['path']}`](../{p['path']}). Maintainer: {cell(p['maintainer'])}.", ""]
            if p["skills"]:
                out += ["| Tier | Plugin | Skill | What it does | Trigger phrases | Example prompt | Maintainer |",
                        "| --- | --- | --- | --- | --- | --- | --- |"]
                for s in p["skills"]:
                    out.append(
                        f"| {p['tier']} | {p['name']} | [`{s['name']}`](../{s['path']}) | {cell(s['does'])} | "
                        f"{cell(s['triggers'])} | {cell(s['example'])} | {cell(s['maintainer'])} |")
            else:
                out.append("This plugin has no skills.")
            if p["commands"]:
                out += ["", "**Commands.** Type the command in Claude Code, with any arguments after it. "
                        "The short form without the plugin prefix also works when no other command has that name.", ""]
                out += [f"- [`/{p['name']}:{c['name']}`](../{c['path']}): {cell(c['description'])}"
                        for c in p["commands"]]
            if p["agents"]:
                out += ["", "**Agents.** Claude delegates to an agent when the task fits; to choose one yourself, "
                        "ask for it by name (for example, \"use the "
                        f"{p['agents'][0]['name']} agent to ...\").", ""]
                out += [f"- [`{a['name']}`](../{a['path']}): {cell(a['description'])}" for a in p["agents"]]
    return "\n".join(out) + "\n"


# --- commands -------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["sync", "check"])
    ap.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    root = args.root

    meta, plugins, errors = load(root)
    if errors:
        print("\n".join(f"error: {e}" for e in errors), file=sys.stderr)
        return 1
    text = render(meta, plugins)
    target = root / OUTPUT
    if args.command == "sync":
        target.write_text(text, encoding="utf-8")
        print(f"wrote {OUTPUT}")
        return 0
    if not target.is_file() or target.read_text(encoding="utf-8") != text:
        print(f"error: {OUTPUT} is out of date; run `pixi run catalog-sync` and commit the result",
              file=sys.stderr)
        return 1
    print(f"{OUTPUT} is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
