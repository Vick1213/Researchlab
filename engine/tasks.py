"""Load replay tasks and score candidates against their oracles.

Layout of a task directory (tasks/<id>/):
  task.yaml        oracle config and variants
  pack_*.md        knowledge packs (shown to the solver)
  data/            data shown to the solver
  hidden/          held-out data and ground truth (never shown to the solver)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from oracles import law_fit

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"


@dataclass
class Variant:
    task_id: str
    name: str
    dir: Path
    spec: dict
    oracle: dict

    @property
    def pack_text(self) -> str:
        return (self.dir / self.spec["pack"]).read_text()

    @property
    def train_path(self) -> Path:
        return self.dir / self.spec["train"]

    @property
    def holdout_path(self) -> Path | None:
        h = self.spec.get("holdout")
        return self.dir / h if h else None

    def visible_files(self) -> list[Path]:
        """Everything the solver is allowed to see besides the pack."""
        files = [self.train_path]
        assert all("hidden" not in p.relative_to(self.dir).parts for p in files), "hidden file exposed"
        return files


def load(task_id: str, variant: str) -> Variant:
    d = TASKS_DIR / task_id
    task = yaml.safe_load((d / "task.yaml").read_text())
    if variant not in task["variants"]:
        raise KeyError(f"{task_id} has no variant {variant!r}; choose from {list(task['variants'])}")
    return Variant(task_id, variant, d, task["variants"][variant], task["oracle"])


def score(v: Variant, candidate: dict) -> dict:
    kind = v.oracle["kind"]
    if kind != "law_fit":
        raise NotImplementedError(f"oracle kind {kind!r}")
    obs = v.spec["observables"]
    cfg = law_fit.OracleConfig.from_task(obs, v.oracle.get("thresholds"))
    columns = {k: o["column"] for k, o in obs.items()}
    train = law_fit.load_table(v.train_path, columns)
    holdout = law_fit.load_table(v.holdout_path, columns) if v.holdout_path else None
    return law_fit.evaluate(candidate, cfg, train, holdout).to_dict()
