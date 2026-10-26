"""Turn a model reply into an oracle verdict and a scalar reward."""
from __future__ import annotations

import math

from engine import prompts, tasks

# Reward schemes. "binary" is the default and the one to train on first: shaped
# rewards give partial credit that RL will exploit (e.g. a law that parses and has
# consistent units but fits nothing).
SCHEMES = {
    "binary": None,
    "shaped": {"parse": 0.05, "dimensions": 0.05, "parsimony": 0.1, "train_fit": 0.3, "holdout_transfer": 0.5},
}


def score_reply(v: tasks.Variant, text: str) -> tuple[dict | None, dict]:
    """Return (candidate, oracle_result). Never raises on a bad reply."""
    try:
        candidate = prompts.extract_candidate(text)
    except ValueError as e:
        return None, {"passed": False, "checks": {"extract": False}, "errors": [f"extract: {e}"]}
    try:
        return candidate, tasks.score(v, candidate)
    except Exception as e:  # noqa: BLE001 - a malformed candidate must not crash a run
        return candidate, {"passed": False, "checks": {"extract": True, "score": False},
                           "errors": [f"score: {type(e).__name__}: {e}"]}


def reward(oracle: dict, scheme: str = "binary", complexity_penalty: float = 0.0) -> float:
    """Scalar reward in [0, 1] from an oracle result."""
    if scheme not in SCHEMES:
        raise KeyError(f"unknown reward scheme {scheme!r}; choose from {list(SCHEMES)}")
    weights = SCHEMES[scheme]
    if weights is None:
        r = 1.0 if oracle.get("passed") else 0.0
    else:
        checks = oracle.get("checks", {})
        r = sum(w for name, w in weights.items() if checks.get(name))
    if complexity_penalty and r > 0:
        c = oracle.get("metrics", {}).get("complexity", 0.0)
        if math.isfinite(c):
            r = max(0.0, r - complexity_penalty * c)
    return float(r)
