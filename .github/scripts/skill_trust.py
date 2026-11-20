#!/usr/bin/env python3
"""Helpers for the skill trust pilot (security gate over SkillEvaluator Tier 1 reports).

select-pilot  Read skill directories on stdin and print the pilot ones.

gate          Read each skill's skillevaluator-output-*.json and print a Markdown
              table for the job summary. A skill fails on any unaccepted
              high/critical finding, any accepted-findings entry that no longer
              matches, an incomplete scan, or a missing/unreadable report.
              Exits 1 if any skill fails.

Usage:
    python skill_trust.py select-pilot < skills.txt
    python skill_trust.py gate --reports <dir> --skills <file> --accepted .github/skill-security-accepted.yml
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# supply-chain-security is deferred; re-adding it is a one-line change here.
PILOT_PLUGINS: tuple[str, ...] = ("ai-research-workflows",)
BLOCKING_SEVERITIES = {"high", "critical"}
FIELDS = ("skill", "check_name", "file_path", "line_content", "file_sha256", "reason")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def report_name(skill_dir: str) -> str:
    """Report subdirectory for a skill; matches skill-quality.py."""
    return skill_dir.replace("/", "__")


def is_pilot(skill_dir: str) -> bool:
    m = re.fullmatch(r"plugins/([^/]+)/skills/[^/]+", skill_dir.strip("/"))
    return bool(m) and m.group(1) in PILOT_PLUGINS


@dataclass(frozen=True)
class Acceptance:
    skill: str
    check_name: str
    file_path: str  # relative to the skill dir
    line_content: str
    file_sha256: str  # SHA-256 of the whole flagged file; any edit to it needs re-review
    reason: str


def load_acceptances(path: Path) -> list[Acceptance]:
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(entries, list):
        raise ValueError(f"{path}: expected a list of mappings")
    out = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry {i} is not a mapping")
        for key in FIELDS:
            if key not in entry or entry[key] is None:
                raise ValueError(f"{path}: entry {i} is missing {key!r}")
        if not str(entry["reason"]).strip():
            raise ValueError(f"{path}: entry {i} has an empty reason")
        if not SHA256_RE.fullmatch(str(entry["file_sha256"])):
            raise ValueError(f"{path}: entry {i} file_sha256 must be 64 lowercase hex characters")
        out.append(Acceptance(**{key: str(entry[key]) for key in FIELDS}))
    return out


@dataclass
class GateResult:
    blocking: list[dict] = field(default_factory=list)
    accepted: list[dict] = field(default_factory=list)
    stale: list[Acceptance] = field(default_factory=list)
    incomplete: bool = False

    @property
    def passed(self) -> bool:
        return not (self.blocking or self.stale or self.incomplete)


def relative_path(file_path: str, skill: str) -> str:
    """Make a finding's path relative to the skill dir (scans record absolute paths)."""
    marker = skill.rstrip("/") + "/"
    if marker in file_path:
        return file_path.rsplit(marker, 1)[1]
    return file_path


def file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def gate(report: dict, skill: str, acceptances: list[Acceptance], root: Path = Path(".")) -> GateResult:
    results = report.get("results")
    # Fail closed: only a report that says passed/failed and carries a results list is trusted.
    result = GateResult(incomplete=report.get("overall_status") not in ("passed", "failed") or not isinstance(results, list))
    mine = [a for a in acceptances if a.skill == skill]
    used: set[Acceptance] = set()
    digests: dict[str, str | None] = {}

    def digest_matches(a: Acceptance) -> bool:
        if a.file_path not in digests:
            digests[a.file_path] = file_digest(root / skill / a.file_path)
        return digests[a.file_path] == a.file_sha256

    for res in results if isinstance(results, list) else []:
        for f in res.get("findings") or []:
            if str(f.get("severity", "")).lower() not in BLOCKING_SEVERITIES:
                continue
            key = (
                f.get("check_name"),
                relative_path(f.get("file_path") or "", skill),
                (f.get("line_content") or "").strip(),
            )
            match = next((a for a in mine if (a.check_name, a.file_path, a.line_content.strip()) == key and digest_matches(a)), None)
            if match:
                used.add(match)
                result.accepted.append(f)
            else:
                result.blocking.append(f)
    result.stale = [a for a in mine if a not in used]
    return result


def read_report(reports: Path, skill: str) -> dict | None:
    """Newest skillevaluator-output-*.json for the skill (the suffix is a timestamp)."""
    candidates = sorted((reports / report_name(skill)).glob("skillevaluator-output-*.json"), key=lambda p: p.name)
    if not candidates:
        return None
    try:
        data = json.loads(candidates[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def summarize(reports: Path, skills: list[str], acceptances: list[Acceptance], root: Path = Path(".")) -> tuple[str, bool]:
    lines = [
        "### Skill security gate (SkillEvaluator Tier 1, high/critical findings)",
        "",
        "| Skill | Blocking | Accepted | Stale | Result |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    ok = True
    for skill in skills:
        report = read_report(reports, skill)
        if report is None:
            lines.append(f"| `{skill}` | — | — | — | ❌ no readable report |")
            ok = False
            continue
        res = gate(report, skill, acceptances, root)
        if res.incomplete:
            verdict = "❌ scan incomplete"
        elif res.passed:
            verdict = "✅ pass"
        else:
            verdict = "❌ fail"
        ok = ok and res.passed
        lines.append(f"| `{skill}` | {len(res.blocking)} | {len(res.accepted)} | {len(res.stale)} | {verdict} |")
    if not skills:
        lines.append("| _no skills selected_ | | | | |")
    return "\n".join(lines) + "\n", ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select-pilot")
    g = sub.add_parser("gate")
    g.add_argument("--reports", type=Path, required=True)
    g.add_argument("--skills", type=Path, required=True, help="file with one skill directory per line")
    g.add_argument("--accepted", type=Path, required=True, help="accepted-findings YAML file")
    g.add_argument("--root", type=Path, default=Path("."), help="repo root that skill directories are relative to")
    args = ap.parse_args(argv)

    if args.cmd == "select-pilot":
        pilot = [s for s in (line.strip() for line in sys.stdin) if s and is_pilot(s)]
        if pilot:
            print("\n".join(pilot))
        return 0
    skills = [s for s in (line.strip() for line in args.skills.read_text(encoding="utf-8").splitlines()) if s]
    try:
        acceptances = load_acceptances(args.accepted)
    except (yaml.YAMLError, OSError, ValueError) as exc:
        print(f"error: cannot load accepted findings {args.accepted}: {' '.join(str(exc).split())}", file=sys.stderr)
        return 1
    table, ok = summarize(args.reports, skills, acceptances, args.root)
    sys.stdout.write(table)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
