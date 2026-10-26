"""Command line: python -m engine <command> ...

  plan        experiments/x.yaml                 show what a run would do; no calls
  run         experiments/x.yaml [--allow-model-calls] [--backend SPEC ...]
  prompt      TASK VARIANT                        print the prompt a solver would send
  score       TASK VARIANT REPLY_FILE             score a saved reply with the oracle
  backends                                        list registered backends
  export-prompts  OUT.jsonl TASK:VARIANT ... [--repeats N]
  export-trajectories OUT.jsonl RUN_DIR ... [--min-reward R]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine import experiment, prompts, rl, scoring, tasks
from engine.models import available


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m engine", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan"); p.add_argument("config")
    p = sub.add_parser("run"); p.add_argument("config")
    p.add_argument("--allow-model-calls", action="store_true")
    p.add_argument("--backend", action="append", help="override the config's backends (repeatable)")
    p = sub.add_parser("prompt"); p.add_argument("task"); p.add_argument("variant")
    p = sub.add_parser("score"); p.add_argument("task"); p.add_argument("variant"); p.add_argument("reply", type=Path)
    p.add_argument("--scheme", default="binary")
    sub.add_parser("backends")
    p = sub.add_parser("export-prompts"); p.add_argument("out"); p.add_argument("tasks", nargs="+")
    p.add_argument("--repeats", type=int, default=1)
    p = sub.add_parser("export-trajectories"); p.add_argument("out"); p.add_argument("runs", nargs="+")
    p.add_argument("--min-reward", type=float)
    args = ap.parse_args(argv)

    if args.cmd == "plan":
        cfg = experiment.ExperimentConfig.load(args.config)
        rows = experiment.plan(cfg)
        for r in rows:
            print(f"{r['task']}:{r['variant']:<12} {r['backend']:<40} x{r['samples']}  "
                  f"{r['prompt_chars']} chars  sha {r['prompt_sha256']}")
        print(f"total calls (baseline solver): {sum(r['samples'] for r in rows)}")
    elif args.cmd == "run":
        cfg = experiment.ExperimentConfig.load(args.config)
        if args.backend:
            cfg.backends = args.backend
        try:
            out = experiment.run(cfg, allow_model_calls=args.allow_model_calls)
        except experiment.ModelCallsNotAllowed as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        for row in json.loads((out / "summary.json").read_text()):
            print(row)
        print(f"output: {out.relative_to(tasks.ROOT) if out.is_relative_to(tasks.ROOT) else out}")
    elif args.cmd == "prompt":
        print(prompts.build(tasks.load(args.task, args.variant)))
    elif args.cmd == "score":
        candidate, oracle = scoring.score_reply(tasks.load(args.task, args.variant), args.reply.read_text())
        print(json.dumps({"candidate": candidate, "oracle": oracle,
                          "reward": scoring.reward(oracle, args.scheme)}, indent=2))
    elif args.cmd == "backends":
        print("\n".join(available()))
    elif args.cmd == "export-prompts":
        print(f"{rl.export_prompt_dataset(args.tasks, args.out, args.repeats)} rows -> {args.out}")
    elif args.cmd == "export-trajectories":
        print(f"{rl.export_trajectories(args.runs, args.out, args.min_reward)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
