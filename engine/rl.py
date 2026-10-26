"""Hooks for RL and fine-tuning on open-weight models.

The oracle is the reward. Nothing here depends on a training library; the pieces
are shaped so common trainers can use them directly:

- ``TaskEnv``: single-turn environment. ``reset()`` gives the prompt messages,
  ``step(completion)`` gives the reward and the oracle verdict.
- ``reward_fn``: ``(prompts, completions, task, variant, **kw) -> list[float]``, the
  signature of a TRL GRPOTrainer reward function, where ``task`` and ``variant`` are
  columns of the prompt dataset. Not tested against TRL itself (not installed here).
- ``export_prompt_dataset``: JSONL of prompts for on-policy training.
- ``export_trajectories``: JSONL of (prompt, completion, reward) from finished runs,
  for rejection-sampling fine-tuning or offline RL.

Caveat: the historical tasks are contaminated, so training on them rewards recall.
Train on synthetic variants and keep historical and post-cutoff tasks for evaluation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from engine import prompts, scoring, tasks
from engine.experiment import load_records


def _completion_text(completion: Any) -> str:
    """Accept a plain string or a conversational completion (list of messages)."""
    if isinstance(completion, str):
        return completion
    if isinstance(completion, list):
        return "".join(m.get("content", "") for m in completion if m.get("role") == "assistant")
    raise TypeError(f"unsupported completion type {type(completion).__name__}")


@dataclass
class StepResult:
    reward: float
    oracle: dict
    candidate: dict | None


class TaskEnv:
    """One task variant as a single-turn environment."""

    def __init__(self, task_id: str, variant: str, scheme: str = "binary", complexity_penalty: float = 0.0):
        self.variant = tasks.load(task_id, variant)
        self.scheme = scheme
        self.complexity_penalty = complexity_penalty

    def reset(self) -> list[dict]:
        return [{"role": "user", "content": prompts.build(self.variant)}]

    def step(self, completion: Any) -> StepResult:
        candidate, oracle = scoring.score_reply(self.variant, _completion_text(completion))
        return StepResult(scoring.reward(oracle, self.scheme, self.complexity_penalty), oracle, candidate)


_ENV_CACHE: dict[tuple, TaskEnv] = {}


def reward_fn(prompts: list, completions: list, task: list[str], variant: list[str],
              scheme: str = "binary", **_: Any) -> list[float]:
    """Batch reward. Extra keyword arguments (other dataset columns) are ignored."""
    out = []
    for completion, t, v in zip(completions, task, variant):
        key = (t, v, scheme)
        if key not in _ENV_CACHE:
            _ENV_CACHE[key] = TaskEnv(t, v, scheme)
        out.append(_ENV_CACHE[key].step(completion).reward)
    return out


def export_prompt_dataset(task_specs: Iterable[str], path: str | Path, repeats: int = 1) -> int:
    """Write one JSONL row per (task, variant, repeat): prompt messages plus routing columns."""
    rows = 0
    with open(path, "w") as f:
        for spec in task_specs:
            task_id, _, variant = spec.partition(":")
            env = TaskEnv(task_id, variant)
            for _ in range(repeats):
                f.write(json.dumps({"prompt": env.reset(), "task": task_id, "variant": variant}) + "\n")
                rows += 1
    return rows


def export_trajectories(run_dirs: Iterable[str | Path], path: str | Path,
                        min_reward: float | None = None) -> int:
    """Flatten finished runs into (prompt, completion, reward) rows.

    ``min_reward`` keeps only rows at or above a threshold (rejection sampling).
    Records with a backend error are skipped.
    """
    rows = 0
    with open(path, "w") as f:
        for run_dir in run_dirs:
            for rec in load_records(run_dir):
                if rec["error"] is not None or not rec["calls"]:
                    continue
                if min_reward is not None and rec["reward"] < min_reward:
                    continue
                first = rec["calls"][0]["request"]
                f.write(json.dumps({
                    "prompt": [{"role": m["role"], "content": m["content"]} for m in first["messages"]],
                    "completion": [{"role": "assistant", "content": rec["reply"]}],
                    "reward": rec["reward"],
                    "passed": bool(rec["oracle"].get("passed")),
                    "task": rec["task"], "variant": rec["variant"],
                    "backend": rec["backend"], "solver": rec["solver"], "record_id": rec["id"],
                }) + "\n")
                rows += 1
    return rows
