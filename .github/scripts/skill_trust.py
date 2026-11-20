#!/usr/bin/env python3
"""Helpers for the skill trust pilot (security gate over SkillEvaluator Tier 1 reports).

select-pilot  Read skill directories on stdin and print the pilot ones.

gate          Read each skill's skillevaluator-output-*.json and print a Markdown
              table for the job summary. A skill fails on any unaccepted
              high/critical finding, any accepted-findings entry that no longer
              matches, an incomplete scan, or a missing/unreadable report.
              Exits 1 if any skill fails.

changed-plugins  Print the plugin directories changed since a tag, ignoring
              skill evidence files (evals, BENCHMARK.md, skill-card.md).

check         Check every pilot skill's trust evidence: the five capability
              declarations and a skill-card.md with every required section.
              Exits 1 if any skill has an error.

list-pilot    Print the pilot skill directories, or validate a comma-separated
              --skills list (each must be an existing pilot skill directory).
              Exits 1 on the first entry that is not.

collect-benchmarks  Copy each skill's <reports>/<report_name>/BENCHMARK.md to
              <skill>/BENCHMARK.md. A skill without one is listed as missing and
              left untouched (benchmarks are advisory, so this is not an error).

stage         Copy each pilot skill directory to <out>/<plugin>--<skill>/ (files only;
              a symlink inside a skill is an error). The release workflow signs
              each staged directory, then packs it.

pack          Write <out>/<plugin>--<skill>-<version>.tar.gz from a signed staged
              directory (it must hold skill.oms.sig). Deterministic: sorted
              members, zero mtime/uid/gid, fixed gzip header.

Usage:
    python skill_trust.py select-pilot < skills.txt
    python skill_trust.py list-pilot [--skills a,b]
    python skill_trust.py collect-benchmarks --reports <dir> [--skills a,b]
    python skill_trust.py check [--no-evals]
    python skill_trust.py changed-plugins <previous-tag>
    python skill_trust.py stage --out DIR
    python skill_trust.py pack --staged DIR --version 26.11.0 --out DIR
    python skill_trust.py gate --reports <dir> --skills <file> --accepted .github/skill-security-accepted.yml
"""

import argparse
import fnmatch
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# supply-chain-security is deferred; re-adding it is a one-line change here.
PILOT_PLUGINS: tuple[str, ...] = ("ai-research-workflows",)
BLOCKING_SEVERITIES = {"high", "critical"}
FIELDS = ("skill", "check_name", "file_path", "line_content", "file_sha256", "reason")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
PLUGIN_ROOTS = ("plugins", "community-plugins")
# Evidence about a skill, not part of the skill. Relative to a plugin directory;
# matched segment by segment, so `*` never crosses `/` and a trailing `**` means
# "anything below".
EVIDENCE_PATTERNS: tuple[str, ...] = ("skills/*/evals/**", "skills/*/BENCHMARK.md", "skills/*/skill-card.md")


# What a skill directs the agent to do (not what code it ships), declared under
# `metadata` in SKILL.md frontmatter. A reviewer checks the values against the content.
CAPABILITIES: dict[str, frozenset[str]] = {
    "capability-network": frozenset({"none", "read", "write"}),
    "capability-shell": frozenset({"none", "runs-commands"}),
    "capability-file": frozenset({"none", "read", "write"}),
    "capability-environment": frozenset({"none", "read"}),
    "capability-mcp": frozenset({"none", "uses"}),
}


def check_capabilities(frontmatter: dict) -> list[str]:
    """Errors for a skill's frontmatter: each capability key must exist under metadata with an allowed value."""
    metadata = frontmatter.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    errors = []
    for key, allowed in CAPABILITIES.items():
        if key not in metadata:
            errors.append(f"metadata.{key}: missing (one of {sorted(allowed)})")
        elif metadata[key] not in allowed:
            errors.append(f"metadata.{key}: {metadata[key]!r} is not one of {sorted(allowed)}")
    return errors


# Required H2 headings of a skill card (matched case-insensitively), following
# NVIDIA's Skill Card template (NVIDIA/Trustworthy-AI).
SKILL_CARD_SECTIONS: tuple[str, ...] = (
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
CARD_FILE = "skill-card.md"
H2_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def read_frontmatter(skill_md: Path) -> dict | None:
    """Parsed YAML frontmatter of a SKILL.md, or None if absent or unreadable."""
    try:
        parts = skill_md.read_text(encoding="utf-8").split("---\n", 2)
        fm = yaml.safe_load(parts[1]) if len(parts) == 3 and parts[0] == "" else None
    except (OSError, yaml.YAMLError):
        return None
    return fm if isinstance(fm, dict) else None


def check_card(skill_dir: Path) -> list[str]:
    """Errors for a skill's skill-card.md: it must exist and carry every required H2 section."""
    try:
        text = (skill_dir / CARD_FILE).read_text(encoding="utf-8")
    except OSError:
        return [f"{CARD_FILE}: missing or unreadable"]
    headings = {re.sub(r"(\s*(<br>|:))+\s*$", "", h).strip().casefold() for h in H2_RE.findall(text)}
    return [f"{CARD_FILE}: missing section '## {s}'" for s in SKILL_CARD_SECTIONS if s.casefold() not in headings]


def check_skill(skill_dir: Path, require_evals: bool = True) -> list[str]:
    """All trust-evidence errors for one skill. Task 7 adds the evals check behind require_evals."""
    frontmatter = read_frontmatter(skill_dir / "SKILL.md")
    if frontmatter is None:
        errors = ["SKILL.md: frontmatter missing or unreadable"]
    else:
        errors = check_capabilities(frontmatter)
    return errors + check_card(skill_dir)


def report_name(skill_dir: str) -> str:
    """Report subdirectory for a skill; matches skill-quality.py."""
    return skill_dir.replace("/", "__")


def is_pilot(skill_dir: str) -> bool:
    m = re.fullmatch(r"plugins/([^/]+)/skills/[^/]+", skill_dir.strip("/"))
    return bool(m) and m.group(1) in PILOT_PLUGINS


def resolve_skills(root: Path, csv: str = "") -> list[str]:
    """Pilot skill dirs: all of them for an empty csv, else the validated, de-duplicated csv entries."""
    if not csv.strip():
        return sorted(
            d.relative_to(root).as_posix()
            for p in PILOT_PLUGINS
            for d in (root / "plugins" / p / "skills").glob("*/")
            if d.is_dir()
        )
    skills: list[str] = []
    for raw in csv.split(","):
        skill = raw.strip().strip("/")
        if not skill:
            continue
        if not is_pilot(skill) or skill.split("/")[-1] in (".", "..") or not (root / skill).is_dir():
            raise ValueError(f"{raw.strip()!r} is not a pilot skill directory")
        if skill not in skills:
            skills.append(skill)
    return skills


def collect_benchmarks(reports: Path, root: Path, skills: list[str]) -> tuple[list[str], list[str]]:
    """Copy each skill's BENCHMARK.md from its report dir into the skill; return (updated, missing)."""
    updated, missing = [], []
    for skill in skills:
        source = reports / report_name(skill) / "BENCHMARK.md"
        if source.is_file():
            shutil.copyfile(source, root / skill / "BENCHMARK.md")
            updated.append(skill)
        else:
            missing.append(skill)
    return updated, missing


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


def is_evidence(relpath: str) -> bool:
    """True if a plugin-relative path is skill evidence rather than a plugin change."""
    parts = relpath.split("/")
    for pattern in EVIDENCE_PATTERNS:
        pp = pattern.split("/")
        if pp[-1] == "**":
            ok = len(parts) > len(pp) - 1 and all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pp[:-1]))
        else:
            ok = len(parts) == len(pp) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pp))
        if ok:
            return True
    return False


def changed_plugins(root: Path, since: str) -> list[str]:
    """Plugin dirs with a changed path outside the evidence patterns since `since`."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{since}..HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout
    changed: set[str] = set()
    for line in out.splitlines():
        parts = line.strip().split("/", 2)
        if len(parts) == 3 and parts[0] in PLUGIN_ROOTS and not is_evidence(parts[2]):
            changed.add(f"{parts[0]}/{parts[1]}")
    return sorted(changed)


SIGNATURE_NAME = "skill.oms.sig"
# Calendar tag without the leading `v` (docs/versioning.md): YY.M.MICRO, month 1-12 with no padding.
VERSION_RE = re.compile(r"\d{2}\.(?:[1-9]|1[0-2])\.(?:0|[1-9]\d*)")


def stage(root: Path, out: Path) -> list[Path]:
    """Copy each pilot skill directory to out/<plugin>--<skill>/ and return the staged directories.

    Files only: a symlink anywhere in a skill is an error, so nothing outside the skill is copied.
    """
    staged = []
    for plugin in PILOT_PLUGINS:
        for skill_dir in sorted((root / "plugins" / plugin / "skills").glob("*/")):
            if not skill_dir.is_dir():
                continue
            for path in [skill_dir, *skill_dir.rglob("*")]:
                if path.is_symlink():
                    raise ValueError(f"{path.relative_to(root)}: symlink in a skill; refusing to stage it")
            dest = out / f"{plugin}--{skill_dir.name}"
            shutil.copytree(skill_dir, dest, symlinks=True)
            staged.append(dest)
    return staged


def pack(staged: Path, version: str, out: Path) -> Path:
    """Write out/<staged name>-<version>.tar.gz with archive root <staged name>/ and return its path."""
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"version {version!r} is not a calendar version like 26.11.0")
    if not (staged / SIGNATURE_NAME).is_file():
        raise ValueError(f"{staged}: {SIGNATURE_NAME} is missing; sign the directory before packing")
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"{staged.name}-{version}.tar.gz"
    with open(archive, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar:
            for path in [staged, *sorted(staged.rglob("*"))]:
                info = tar.gettarinfo(str(path), arcname=f"{staged.name}/{path.relative_to(staged)}".removesuffix("/."))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.mode = 0o755 if path.is_dir() else 0o644
                if path.is_file():
                    with open(path, "rb") as fh:
                        tar.addfile(info, fh)
                else:
                    tar.addfile(info)
    return archive


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("select-pilot")
    g = sub.add_parser("gate")
    g.add_argument("--reports", type=Path, required=True)
    g.add_argument("--skills", type=Path, required=True, help="file with one skill directory per line")
    g.add_argument("--accepted", type=Path, required=True, help="accepted-findings YAML file")
    g.add_argument("--root", type=Path, default=Path("."), help="repo root that skill directories are relative to")
    c = sub.add_parser("check")
    c.add_argument("--no-evals", action="store_true", help="skip the evals check")
    c.add_argument("--root", type=Path, default=Path("."), help="repo root that plugins/ is under")
    cp = sub.add_parser("changed-plugins")
    cp.add_argument("since", help="previous release tag (or any git revision)")
    cp.add_argument("--root", type=Path, default=Path("."), help="repo root")
    lp = sub.add_parser("list-pilot")
    lp.add_argument("--skills", default="", help="comma-separated skill directories (empty = all pilot skills)")
    lp.add_argument("--root", type=Path, default=Path("."), help="repo root")
    cb = sub.add_parser("collect-benchmarks")
    cb.add_argument("--reports", type=Path, required=True, help="directory of per-skill report subdirectories")
    cb.add_argument("--skills", default="", help="comma-separated skill directories (empty = all pilot skills)")
    cb.add_argument("--root", type=Path, default=Path("."), help="repo root that skill directories are relative to")
    sg = sub.add_parser("stage")
    sg.add_argument("--out", type=Path, required=True, help="directory to stage the pilot skills into")
    sg.add_argument("--root", type=Path, default=Path("."), help="repo root")
    pk = sub.add_parser("pack")
    pk.add_argument("--staged", type=Path, required=True, help="directory holding the signed staged skill directories")
    pk.add_argument("--version", required=True, help="release version without the leading v, e.g. 26.11.0")
    pk.add_argument("--out", type=Path, required=True, help="directory for the archives")
    args = ap.parse_args(argv)

    if args.cmd == "stage":
        try:
            for d in stage(args.root, args.out):
                print(d)
        except (ValueError, FileExistsError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "pack":
        try:
            dirs = sorted(d for d in args.staged.iterdir() if d.is_dir())
            if not dirs:
                raise ValueError(f"{args.staged}: no staged skill directories")
            for d in dirs:
                print(pack(d, args.version, args.out))
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.cmd in ("list-pilot", "collect-benchmarks"):
        try:
            skills = resolve_skills(args.root, args.skills)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.cmd == "list-pilot":
            if skills:
                print("\n".join(skills))
            return 0
        updated, missing = collect_benchmarks(args.reports, args.root, skills)
        for skill in updated:
            print(f"updated: {skill}")
        for skill in missing:
            print(f"missing: {skill}")
        return 0
    if args.cmd == "changed-plugins":
        try:
            changed = changed_plugins(args.root, args.since)
        except subprocess.CalledProcessError as exc:
            print(f"error: {' '.join(exc.stderr.split())}", file=sys.stderr)
            return 1
        if changed:
            print("\n".join(changed))
        return 0
    if args.cmd == "check":
        skill_dirs = sorted(d for p in PILOT_PLUGINS for d in (args.root / "plugins" / p / "skills").glob("*/") if d.is_dir())
        if not skill_dirs:
            print("error: no pilot skills found", file=sys.stderr)
            return 1
        failed = 0
        for d in skill_dirs:
            errors = check_skill(d, require_evals=not args.no_evals)
            for e in errors:
                print(f"{d.relative_to(args.root)}: {e}", file=sys.stderr)
            failed += bool(errors)
        print(f"trust-check: {len(skill_dirs) - failed}/{len(skill_dirs)} pilot skills pass")
        return 1 if failed else 0
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
