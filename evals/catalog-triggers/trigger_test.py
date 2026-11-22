#!/usr/bin/env python3
"""Check that each example prompt in docs/catalog.yml activates its skill in Claude Code.

Runs every prompt in headless Claude Code (`claude -p`) with all of this
repository's plugins loaded and nothing else: user settings, hooks and MCP
servers are left out, and each run starts in an empty temporary directory.
A run stops at the first Skill tool call, or after --max-turns.

A prompt passes when the first skill Claude invokes is the catalog's skill, or
a command listed in DELEGATES that only hands the request to that skill. A
ROUTERS skill, whose job is to pick another skill, doesn't end the run: the
run stops at the next skill invoked, and both count.

Usage (from the repository root; needs the `claude` CLI, logged in):

    pixi run -e ci python evals/catalog-triggers/trigger_test.py                 # every skill
    pixi run -e ci python evals/catalog-triggers/trigger_test.py zarr-data-format/zarr-fundamentals
    pixi run -e ci python evals/catalog-triggers/trigger_test.py --model sonnet --jobs 4
    pixi run -e ci python evals/catalog-triggers/trigger_test.py --verbose zarr-data-format/zarr-fundamentals

Each run costs a model call, so a full pass over every skill is not free. One
JSON line per skill goes to evals/catalog-triggers/out/results.jsonl.

With --fixtures, it runs each skill's trigger fixture instead
(evals/catalog-triggers/fixtures/<plugin>/<skill>.json: prompts that must
load the skill and neighboring prompts that must not), --repeats times each:

    pixi run -e ci python evals/catalog-triggers/trigger_test.py --fixtures                      # every skill, 3 repeats
    pixi run -e ci python evals/catalog-triggers/trigger_test.py --fixtures zarr-data-format/zarr-fundamentals
    pixi run -e ci python evals/catalog-triggers/trigger_test.py --fixtures --summary results.md # also write a report

A `fire` run passes when the first skill invoked is the target (or a DELEGATES
command for it); a `no-fire` run passes when the first skill invoked is
anything else, or nothing. A case passes when at least --threshold of its
repeats pass (default 2/3), and a skill passes when every one of its cases
does. Use --model to pick the model; to route through a LiteLLM gateway, set
ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN in the environment.
Model output varies, so a single failure can be noise: rerun it before
rewording the prompt or the skill's description.

Logging goes to stderr via the standard `logging` module so it never mixes
with the per-job PASS/FAIL lines or the results file on stdout. By default a
job where no skill gets invoked logs a warning with the tools it did call,
the last assistant text, and the final result event; subprocess stderr is
always logged. Pass --verbose to also log every stream-json event (including
the exact `claude` command line) for every job, not just the failing ones.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import logging
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"
log = logging.getLogger("trigger_test")

# Commands whose body is only "Use the `<plugin>:<skill>` skill", so invoking
# them activates that skill.
DELEGATES = {
    "ai-research-workflows:experiment": "running-experiments",
    "ai-research-workflows:handoff": "creating-handoffs",
    "ai-research-workflows:harden": "hardening-research-code",
    "ai-research-workflows:implement": "implementing-plans",
    "ai-research-workflows:iterate-plan": "iterating-plans",
    "ai-research-workflows:plan": "planning-implementations",
    "ai-research-workflows:reproduce": "ensuring-reproducibility",
    "ai-research-workflows:research": "researching",
    "ai-research-workflows:validate": "validating-implementations",
    "research-software-design:discover-personas": "user-persona-discovery",
    "zarr-chunk-optimization:rechunk": "rechunking",
    "zarr-chunk-optimization:generate-synthetic": "synthetic-data",
}


# Skills whose job is to pick another skill. A run keeps going past one of these
# and stops at the next skill invoked, so a router that hands off counts for the
# skill it hands off to.
ROUTERS = {"ai-research-workflows:using-research-workflows", "using-research-workflows"}


def _truncate(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _summarize_result(event: dict) -> dict:
    return {k: (_truncate(v) if isinstance(v, str) else v)
            for k, v in event.items() if k in ("subtype", "is_error", "num_turns", "result")}


def run(job: dict, plugin_args: list[str], max_turns: int, model: str | None) -> dict:
    plugin, skill, prompt = job["plugin"], job["skill"], job["prompt"]
    prefix = f"{plugin}/{skill}" + (f" {job['case']}#{job['repeat']}" if "case" in job else "")
    cmd = ["claude", "-p", prompt, *plugin_args, "--setting-sources", "project", "--strict-mcp-config",
           "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns),
           "--no-session-persistence"]
    if model:
        cmd += ["--model", model]
    log.debug("%s cmd: %s", prefix, " ".join(cmd))
    invoked: list[str] = []
    tools: list[str] = []
    last_text: str | None = None
    result_event: dict | None = None
    stderr_output = ""
    with tempfile.TemporaryDirectory(prefix="catalog-trigger-") as cwd:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    log.debug("%s unparseable stdout line: %s", prefix, line.rstrip())
                    continue
                etype = event.get("type")
                log.debug("%s event: %s", prefix, etype)
                if etype == "assistant":
                    for block in event["message"]["content"]:
                        kind = block.get("type")
                        if kind == "text":
                            last_text = block.get("text")
                            log.debug("%s assistant text: %s", prefix, _truncate(last_text or ""))
                        if kind == "tool_use":
                            tools.append(block["name"])
                            log.debug("%s tool_use: %s %r", prefix, block["name"], block.get("input"))
                            if block["name"] == "Skill":
                                invoked.append(block["input"].get("skill") or block["input"].get("command") or "")
                    if invoked and invoked[-1] not in ROUTERS:
                        break
                if etype == "result":
                    result_event = event
                    log.debug("%s result: %s", prefix, event)
                    break
        finally:
            proc.kill()
            proc.wait()
            # Read whatever is left on stderr now that the process has exited.
            # Not read concurrently, so a subprocess that blocks on a full
            # stderr pipe before exiting would stall here too -- not a
            # concern for this CLI, which only writes brief error messages.
            stderr_output = proc.stderr.read()
    if stderr_output.strip():
        log.warning("%s stderr: %s", prefix, stderr_output.strip())
    # The skill that took the request: the first one invoked that isn't a router,
    # or the router itself if it handed off to nothing.
    first = next((i for i in invoked if i not in ROUTERS), invoked[0] if invoked else None)
    fired = any(i in (f"{plugin}:{skill}", skill) or DELEGATES.get(i) == skill for i in invoked)
    passed = fired if job.get("expect", "fire") == "fire" else not fired
    if first is None and job.get("expect", "fire") == "fire":
        log.warning(
            "%s no skill invoked (tools called: %s)%s%s", prefix,
            ", ".join(tools) or "none",
            f"; last assistant text: {_truncate(last_text)}" if last_text else "",
            f"; result: {_summarize_result(result_event)}" if result_event else "",
        )
    extra = {k: job[k] for k in ("case", "kind", "expect", "owner", "repeat") if k in job}
    return {"plugin": plugin, "skill": skill, "prompt": prompt, **extra, "invoked": first, "pass": passed,
            "skills": invoked, "tools": tools}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="plugin/skill pairs to test (default: all)")
    ap.add_argument("--jobs", type=int, default=6, help="parallel runs (default 6)")
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--model", help="model alias or ID (default: Claude Code's default)")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out" / "results.jsonl")
    ap.add_argument("--fixtures", action="store_true",
                    help="run each skill's trigger fixture instead of its catalog example prompt")
    ap.add_argument("--repeats", type=int, default=3, help="runs per fixture case (default 3)")
    ap.add_argument("--threshold", type=Fraction, default=Fraction(2, 3),
                    help="share of a case's repeats that must pass (default 2/3)")
    ap.add_argument("--summary", type=Path, help="with --fixtures, also write a Markdown report here")
    ap.add_argument("--verbose", action="store_true",
                     help="log every stream-json event and the claude command line to stderr "
                          "(default: only subprocess stderr and a warning when no skill is invoked)")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    plugin_args = [a for d in sorted([*ROOT.glob("plugins/*"), *ROOT.glob("community-plugins/*")])
                   for a in ("--plugin-dir", str(d))]
    if args.fixtures:
        jobs = fixture_jobs(args.only, args.repeats)
    else:
        meta = yaml.safe_load((ROOT / "docs/catalog.yml").read_text(encoding="utf-8"))
        jobs = [{"plugin": p, "skill": s, "prompt": m["example"]}
                for p, pm in meta["plugins"].items() for s, m in (pm.get("skills") or {}).items()
                if not args.only or f"{p}/{s}" in args.only]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    with cf.ThreadPoolExecutor(args.jobs) as ex, args.out.open("w", encoding="utf-8") as out:
        for r in ex.map(lambda j: run(j, plugin_args, args.max_turns, args.model), jobs):
            out.write(json.dumps(r) + "\n")
            results.append(r)
            status = "PASS" if r["pass"] else "FAIL"
            case = f" {r['case']}#{r['repeat']} ({r['expect']})" if "case" in r else ""
            print(f"{status} {r['plugin']}/{r['skill']}{case} -> {r['invoked'] or 'no skill'}", flush=True)
    if not args.fixtures:
        failed = sum(not r["pass"] for r in results)
        print(f"\n{len(jobs) - failed}/{len(jobs)} example prompts activated their skill. Results: {args.out}")
        return 1 if failed else 0

    skills = aggregate(results, args.threshold)
    passed = sum(s["pass"] for s in skills.values())
    print(f"\n{passed}/{len(skills)} skills passed their trigger fixtures "
          f"(a case passes at >= {args.threshold} of {args.repeats} runs). Results: {args.out}")
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(report(skills, args, results), encoding="utf-8")
        print(f"Summary: {args.summary}")
    return 0 if passed == len(skills) else 1


def fixture_jobs(only: list[str], repeats: int) -> list[dict]:
    jobs = []
    for path in sorted(FIXTURES.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if only and data["skill"] not in only:
            continue
        plugin, skill = data["skill"].split("/")
        for c in data["cases"]:
            for n in range(1, repeats + 1):
                jobs.append({"plugin": plugin, "skill": skill, "prompt": c["prompt"], "case": c["id"],
                             "kind": c["kind"], "expect": c["expect"], "owner": c.get("owner"), "repeat": n})
    return jobs


def aggregate(results: list[dict], threshold: Fraction) -> dict[str, dict]:
    """Per skill: each case's pass count over its repeats, and whether the skill passes."""
    skills: dict[str, dict] = {}
    for r in results:
        s = skills.setdefault(f"{r['plugin']}/{r['skill']}", {"cases": {}})
        c = s["cases"].setdefault(r["case"], {"kind": r["kind"], "expect": r["expect"], "runs": 0, "passes": 0,
                                               "invoked": []})
        c["runs"] += 1
        c["passes"] += r["pass"]
        c["invoked"].append(r["invoked"])
    for s in skills.values():
        for c in s["cases"].values():
            c["pass"] = Fraction(c["passes"], c["runs"]) >= threshold
        s["pass"] = all(c["pass"] for c in s["cases"].values())
    return dict(sorted(skills.items()))


def report(skills: dict[str, dict], args: argparse.Namespace, results: list[dict]) -> str:
    fire = [r for r in results if r["expect"] == "fire"]
    nofire = [r for r in results if r["expect"] == "no-fire"]
    lines = [
        "# Trigger fixture results",
        "",
        f"- Model: `{args.model or 'Claude Code default'}`",
        f"- Repeats per case: {args.repeats}; a case passes at >= {args.threshold} of its runs",
        f"- Skills passing every case: **{sum(s['pass'] for s in skills.values())}/{len(skills)}**",
        f"- Activation rate on `fire` runs: {sum(r['pass'] for r in fire)}/{len(fire)}",
        f"- False-trigger rate on `no-fire` runs: {sum(not r['pass'] for r in nofire)}/{len(nofire)}",
        "",
        "| Skill | Result | Failing cases (passes/runs, what was invoked) |",
        "| --- | --- | --- |",
    ]
    for name, s in skills.items():
        bad = [f"`{cid}` {c['kind']} {c['passes']}/{c['runs']} ({', '.join(sorted({i or 'none' for i in c['invoked']}))})"
               for cid, c in s["cases"].items() if not c["pass"]]
        lines.append(f"| {name} | {'PASS' if s['pass'] else 'FAIL'} | {'; '.join(bad)} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
