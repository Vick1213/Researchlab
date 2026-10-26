"""Baseline: one plain model call on a task's knowledge pack, no scaffolding.

Examples:
  python -m engine.baseline kepler_third_law historical --print-prompt
  python -m engine.baseline kepler_third_law synthetic                  # calls the API
  python -m engine.baseline kepler_third_law synthetic --response-file reply.md --tag manual
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from engine import prompts, tasks

RUNS_DIR = tasks.ROOT / "eval" / "runs"


def run(task_id: str, variant: str, response_file: Path | None, model: str, effort: str,
        tag: str) -> dict:
    v = tasks.load(task_id, variant)
    prompt = prompts.build(v)
    if response_file:
        reply = {"text": response_file.read_text(), "model_requested": None, "model_served": tag}
    else:
        from engine import llm
        reply = llm.complete(prompt, model=model, effort=effort)

    record = {
        "task": task_id,
        "variant": variant,
        "condition": "baseline",
        "tag": tag,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "effort": None if response_file else effort,
        **{key: val for key, val in reply.items() if key != "text"},
        "reply": reply["text"],
    }
    try:
        record["candidate"] = prompts.extract_candidate(reply["text"])
        record["oracle"] = tasks.score(v, record["candidate"])
    except (ValueError, KeyError) as e:
        record["candidate"] = None
        record["oracle"] = {"passed": False, "errors": [f"extract: {e}"]}
    return record


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task")
    ap.add_argument("variant")
    ap.add_argument("--print-prompt", action="store_true", help="print the prompt and exit")
    ap.add_argument("--response-file", type=Path, help="score a saved reply instead of calling the API")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--tag", default="api", help="label for the run record")
    args = ap.parse_args()

    if args.print_prompt:
        print(prompts.build(tasks.load(args.task, args.variant)))
        return
    record = run(args.task, args.variant, args.response_file, args.model, args.effort, args.tag)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{args.task}_{args.variant}_{args.tag}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    o = record["oracle"]
    print(f"passed={o['passed']} checks={o.get('checks')} metrics={o.get('metrics')}")
    for e in o.get("errors", []):
        print(f"  {e}")
    print(f"record: {out.relative_to(tasks.ROOT)}")


if __name__ == "__main__":
    main()
