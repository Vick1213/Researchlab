"""Run experiments: tasks x backends x samples through one solver, recorded to disk.

An experiment is a YAML file (see experiments/). Output goes to
``eval/runs/<name>/<timestamp>/``:

  manifest.json   config, git commit, package versions, backend descriptions, prompt hashes
  records.jsonl   one line per attempt: calls, reply, candidate, oracle result, reward
  summary.json    pass rate and mean reward per (backend, task, variant)

Backends that run a model are refused unless ``allow_model_calls`` is set, so tests
and dry runs can never spend money by accident.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from engine import prompts, scoring, solvers, tasks
from engine.models import Backend, get_backend

RUNS_DIR = tasks.ROOT / "eval" / "runs"


class ModelCallsNotAllowed(RuntimeError):
    pass


@dataclass
class ExperimentConfig:
    name: str
    tasks: list[str]                       # "task_id:variant"
    backends: list[str]                    # backend spec strings
    solver: str = "baseline"
    solver_options: dict = field(default_factory=dict)
    samples: int = 1
    reward_scheme: str = "binary"
    complexity_penalty: float = 0.0
    max_workers: int = 1

    @classmethod
    def load(cls, path: str | Path) -> "ExperimentConfig":
        raw = yaml.safe_load(Path(path).read_text())
        solver = raw.pop("solver", {"name": "baseline"})
        reward = raw.pop("reward", {})
        return cls(
            solver=solver.get("name", "baseline"),
            solver_options=solver.get("options", {}) or {},
            reward_scheme=reward.get("scheme", "binary"),
            complexity_penalty=reward.get("complexity_penalty", 0.0),
            **raw,
        )

    def task_variants(self) -> list[tasks.Variant]:
        out = []
        for spec in self.tasks:
            task_id, _, variant = spec.partition(":")
            if not variant:
                raise ValueError(f"task {spec!r} must be 'task_id:variant'")
            out.append(tasks.load(task_id, variant))
        return out


def _git_state() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=tasks.ROOT, capture_output=True,
                                  text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def _versions() -> dict:
    out = {"python": platform.python_version()}
    for pkg in ("numpy", "scipy", "sympy", "anthropic"):
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def plan(cfg: ExperimentConfig) -> list[dict]:
    """What a run would do, without calling anything."""
    rows = []
    for v in cfg.task_variants():
        p = prompts.build(v)
        for spec in cfg.backends:
            rows.append({"task": v.task_id, "variant": v.name, "backend": spec,
                         "samples": cfg.samples, "prompt_chars": len(p),
                         "prompt_sha256": hashlib.sha256(p.encode()).hexdigest()[:12]})
    return rows


def _attempt(cfg, solver, backend: Backend, v: tasks.Variant, sample: int) -> dict:
    record = {
        "id": uuid.uuid4().hex,
        "experiment": cfg.name,
        "task": v.task_id,
        "variant": v.name,
        "backend": backend.spec,
        "solver": solver.name,
        "sample": sample,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    try:
        attempt = solver.solve(v, backend, sample)
    except Exception as e:  # noqa: BLE001 - one failed call must not lose the run
        record.update(error=f"{type(e).__name__}: {e}", calls=[], reply=None, candidate=None,
                      oracle={"passed": False, "errors": ["backend error"]}, reward=0.0)
        return record
    candidate, oracle = scoring.score_reply(v, attempt.final_text)
    record.update(
        error=None,
        calls=attempt.calls_as_dicts(),
        reply=attempt.final_text,
        candidate=candidate,
        oracle=oracle,
        reward=scoring.reward(oracle, cfg.reward_scheme, cfg.complexity_penalty),
    )
    return record


def summarize(records: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[(r["backend"], r["task"], r["variant"])].append(r)
    out = []
    for (backend, task, variant), rs in sorted(groups.items()):
        out.append({
            "backend": backend, "task": task, "variant": variant, "n": len(rs),
            "pass_rate": sum(bool(r["oracle"].get("passed")) for r in rs) / len(rs),
            "mean_reward": sum(r["reward"] for r in rs) / len(rs),
            "errors": sum(r["error"] is not None for r in rs),
        })
    return out


def run(cfg: ExperimentConfig, allow_model_calls: bool = False,
        out_root: Path = RUNS_DIR, backends: list[Backend] | None = None) -> Path:
    """Run an experiment and return its output directory.

    ``backends`` overrides the config's spec strings with constructed backends
    (used by tests and by training code that holds a live policy object).
    """
    backends = backends or [get_backend(s) for s in cfg.backends]
    live = [b.spec for b in backends if b.makes_model_calls]
    if live and not allow_model_calls:
        raise ModelCallsNotAllowed(
            f"backends {live} run a model; pass --allow-model-calls to run them")
    solver = solvers.get_solver(cfg.solver, **cfg.solver_options)
    variants = cfg.task_variants()

    out = Path(out_root) / cfg.name / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=False)
    manifest = {
        "config": cfg.__dict__,
        "git": _git_state(),
        "versions": _versions(),
        "backends": [b.describe() for b in backends],
        "plan": plan(cfg),
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    jobs = [(b, v, s) for v in variants for b in backends for s in range(cfg.samples)]
    records = []
    with open(out / "records.jsonl", "w") as f, ThreadPoolExecutor(max_workers=cfg.max_workers) as pool:
        futures = [pool.submit(_attempt, cfg, solver, b, v, s) for b, v, s in jobs]
        for fut in as_completed(futures):
            rec = fut.result()
            records.append(rec)
            f.write(json.dumps(rec) + "\n")
            f.flush()

    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["n_records"] = len(records)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n")
    (out / "summary.json").write_text(json.dumps(summarize(records), indent=2) + "\n")
    return out


def load_records(run_dir: str | Path) -> list[dict]:
    with open(Path(run_dir) / "records.jsonl") as f:
        return [json.loads(line) for line in f if line.strip()]
