#!/usr/bin/env python3
"""Check that each example prompt in docs/catalog.yml activates its skill in Claude Code.

Runs every prompt in headless Claude Code (`claude -p`) with all of this
repository's plugins loaded and nothing else: user settings, hooks and MCP
servers are left out, and each run starts in an empty temporary directory.
A run stops at the first Skill tool call, or after --max-turns.

A prompt passes when the first skill Claude invokes is the catalog's skill, or
a command listed in DELEGATES that only hands the request to that skill.

Usage (from the repository root; needs the `claude` CLI, logged in):

    pixi run -e ci python evals/catalog-triggers/trigger_test.py                 # every skill
    pixi run -e ci python evals/catalog-triggers/trigger_test.py zarr-data-format/zarr-fundamentals
    pixi run -e ci python evals/catalog-triggers/trigger_test.py --model sonnet --jobs 4

Each run costs a model call, so a full pass over every skill is not free. One
JSON line per skill goes to evals/catalog-triggers/out/results.jsonl.
Model output varies, so a single failure can be noise: rerun it before
rewording the prompt or the skill's description.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]

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
}


def run(job: tuple[str, str, str], plugin_args: list[str], max_turns: int, model: str | None) -> dict:
    plugin, skill, prompt = job
    cmd = ["claude", "-p", prompt, *plugin_args, "--setting-sources", "project", "--strict-mcp-config",
           "--output-format", "stream-json", "--verbose", "--max-turns", str(max_turns),
           "--no-session-persistence"]
    if model:
        cmd += ["--model", model]
    invoked: list[str] = []
    tools: list[str] = []
    with tempfile.TemporaryDirectory(prefix="catalog-trigger-") as cwd:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            for line in proc.stdout:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "assistant":
                    for block in event["message"]["content"]:
                        if block.get("type") == "tool_use":
                            tools.append(block["name"])
                            if block["name"] == "Skill":
                                invoked.append(block["input"].get("skill") or block["input"].get("command") or "")
                    if invoked:
                        break
                if event.get("type") == "result":
                    break
        finally:
            proc.kill()
            proc.wait()
    first = invoked[0] if invoked else None
    passed = first in (f"{plugin}:{skill}", skill) or DELEGATES.get(first or "") == skill
    return {"plugin": plugin, "skill": skill, "prompt": prompt, "invoked": first, "pass": passed, "tools": tools}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="plugin/skill pairs to test (default: all)")
    ap.add_argument("--jobs", type=int, default=6, help="parallel runs (default 6)")
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--model", help="model alias or ID (default: Claude Code's default)")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "out" / "results.jsonl")
    args = ap.parse_args(argv)

    meta = yaml.safe_load((ROOT / "docs/catalog.yml").read_text(encoding="utf-8"))
    jobs = [(p, s, m["example"]) for p, pm in meta["plugins"].items() for s, m in (pm.get("skills") or {}).items()
            if not args.only or f"{p}/{s}" in args.only]
    plugin_args = [a for d in sorted([*ROOT.glob("plugins/*"), *ROOT.glob("community-plugins/*")])
                   for a in ("--plugin-dir", str(d))]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    failed = 0
    with cf.ThreadPoolExecutor(args.jobs) as ex, args.out.open("w", encoding="utf-8") as out:
        for r in ex.map(lambda j: run(j, plugin_args, args.max_turns, args.model), jobs):
            out.write(json.dumps(r) + "\n")
            failed += not r["pass"]
            status = "PASS" if r["pass"] else "FAIL"
            print(f"{status} {r['plugin']}/{r['skill']} -> {r['invoked'] or 'no skill'}", flush=True)
    print(f"\n{len(jobs) - failed}/{len(jobs)} example prompts activated their skill. Results: {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
