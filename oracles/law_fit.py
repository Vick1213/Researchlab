"""Oracle for empirical laws: fit a proposed equation to data and check it.

A candidate is a dict (usually parsed from a model's JSON answer):

    {
      "law": "T**2 = k*a**3",
      "parameters": {
        "k": {"units": "time**2/length**3", "system_dependent": true, "initial": 1.0}
      }
    }

Checks, all mechanical:
  1. parse: the law parses and can be solved for the task's target observable.
  2. parsimony: at most ``max_params`` free parameters.
  3. dimensions: both sides have the same dimension once every parameter's units are
     declared. Weak on its own (a free constant can absorb any units) but it rejects
     sums of incommensurable terms and transcendental functions of dimensional inputs.
  4. train fit: least squares in log space; max relative error under a threshold.
  5. holdout transfer: on a held-out system, only parameters marked system_dependent
     are refit; everything else (exponents, structure) must carry over.
"""
from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import sympy as sp
from scipy.optimize import least_squares

from oracles.dimensions import DimensionError, dimension_of, parse_units, same

_RNG_SEED = 0
_N_STARTS = 24
_BAD = 1e3  # residual assigned to non-positive or non-finite predictions


@dataclass
class OracleConfig:
    target: str
    inputs: list[str]
    dimensions: dict[str, str]
    max_params: int = 2
    train_max_rel_err: float = 0.02
    holdout_max_rel_err: float = 0.05

    @classmethod
    def from_task(cls, observables: dict, thresholds: dict | None = None) -> "OracleConfig":
        obs = observables
        target = next(k for k, v in obs.items() if v["role"] == "target")
        inputs = [k for k, v in obs.items() if v["role"] == "input"]
        thresholds = thresholds or {}
        return cls(
            target=target,
            inputs=inputs,
            dimensions={k: v["dimension"] for k, v in obs.items()},
            **thresholds,
        )


@dataclass
class OracleResult:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    fitted_params: dict[str, float] = field(default_factory=dict)
    holdout_params: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def load_table(path: Path, columns: dict[str, str]) -> dict[str, np.ndarray]:
    """Read a CSV and return {observable: array} using the observable -> column map."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return {obs: np.array([float(r[col]) for r in rows]) for obs, col in columns.items()}


def _parse_law(law: str, names: list[str]) -> tuple[sp.Expr, sp.Expr, dict[str, sp.Symbol]]:
    if law.count("=") != 1:
        raise ValueError("law must contain exactly one '='")
    lhs_s, rhs_s = law.split("=")
    syms = {n: sp.Symbol(n, positive=True) for n in names}
    lhs = sp.sympify(lhs_s, locals=syms)
    rhs = sp.sympify(rhs_s, locals=syms)
    return lhs, rhs, syms


def _solve_for(lhs, rhs, target: sp.Symbol) -> list[sp.Expr]:
    sols = sp.solve(sp.Eq(lhs, rhs), target)
    if not sols:
        raise ValueError(f"cannot solve the law for {target}")
    return sols


def _fit(fn, x_cols, y, n_params, fixed_idx, fixed_vals, init, rng):
    """Least squares on log(pred) - log(obs); returns (params, residuals)."""
    free = [i for i in range(n_params) if i not in fixed_idx]

    def full(theta_free):
        theta = np.empty(n_params)
        theta[free] = theta_free
        for i, v in zip(fixed_idx, fixed_vals):
            theta[i] = v
        return theta

    def resid(theta_free):
        with np.errstate(all="ignore"):
            pred = np.asarray(fn(*x_cols, *full(theta_free)), dtype=complex) * np.ones_like(y)
        ok = np.isfinite(pred) & (np.abs(pred.imag) < 1e-9 * np.abs(pred.real) + 1e-300) & (pred.real > 0)
        r = np.full_like(y, _BAD)
        r[ok] = np.log(pred.real[ok]) - np.log(y[ok])
        return r

    if not free:
        theta = full(np.array([]))
        return theta, resid(np.array([]))

    best = None
    base = np.array([init[i] for i in free], dtype=float)
    for k in range(_N_STARTS):
        if k == 0:
            x0 = base
        else:  # random rescaling, with random sign flips on odd starts
            x0 = base * np.exp(rng.normal(0, 2, size=base.shape))
            if k % 2:
                x0 = x0 * rng.choice([1, -1], size=base.shape)
        try:
            sol = least_squares(resid, x0, method="lm" if len(y) >= len(free) else "trf", max_nfev=4000)
        except Exception:  # noqa: BLE001 - a candidate law can blow up the solver in many ways
            continue
        if best is None or sol.cost < best.cost:
            best = sol
    if best is None:
        raise ValueError("fit failed from every starting point")
    return full(best.x), best.fun


def evaluate(candidate: dict, cfg: OracleConfig, train: dict[str, np.ndarray],
             holdout: dict[str, np.ndarray] | None = None) -> OracleResult:
    res = OracleResult(passed=False)
    params_spec: dict = candidate.get("parameters") or {}
    param_names = list(params_spec)
    obs_names = [cfg.target, *cfg.inputs]

    # 1. parse
    try:
        lhs, rhs, syms = _parse_law(candidate["law"], obs_names + param_names)
        unknown = (lhs.free_symbols | rhs.free_symbols) - set(syms.values())
        if unknown:
            raise ValueError(f"undeclared symbols: {sorted(map(str, unknown))}")
        sols = _solve_for(lhs, rhs, syms[cfg.target])
        res.checks["parse"] = True
    except Exception as e:  # noqa: BLE001
        res.checks["parse"] = False
        res.errors.append(f"parse: {e}")
        return res

    # 2. parsimony
    res.metrics["n_params"] = len(param_names)
    res.metrics["complexity"] = float(sp.count_ops(lhs - rhs, visual=False)) + len(param_names)
    res.checks["parsimony"] = len(param_names) <= cfg.max_params
    if not res.checks["parsimony"]:
        res.errors.append(f"parsimony: {len(param_names)} parameters > max {cfg.max_params}")

    # 3. dimensions
    try:
        dims = {syms[n]: parse_units(cfg.dimensions[n]) for n in obs_names}
        param_syms = {n: syms[n] for n in param_names}
        for n, spec in params_spec.items():
            dims[syms[n]] = parse_units(str(spec.get("units", "1")), param_syms)
        dl, dr = dimension_of(lhs, dims), dimension_of(rhs, dims)
        res.checks["dimensions"] = same(dl, dr)
        if not res.checks["dimensions"]:
            res.errors.append(f"dimensions: lhs {dl} != rhs {dr}")
    except (DimensionError, sp.SympifyError, TypeError) as e:
        res.checks["dimensions"] = False
        res.errors.append(f"dimensions: {e}")

    # 4. train fit (try every solution branch, keep the best)
    rng = np.random.default_rng(_RNG_SEED)
    init = [float(params_spec[n].get("initial", 1.0)) for n in param_names]
    arg_syms = [syms[n] for n in cfg.inputs] + [syms[n] for n in param_names]
    x_train = [train[n] for n in cfg.inputs]
    best = None
    for sol in sols:
        fn = sp.lambdify(arg_syms, sol, modules="numpy")
        try:
            theta, r = _fit(fn, x_train, train[cfg.target], len(param_names), [], [], init, rng)
        except ValueError as e:
            res.errors.append(f"train fit: {e}")
            continue
        err = float(np.max(np.abs(np.expm1(r))))
        if best is None or err < best[0]:
            best = (err, fn, theta)
    if best is None:
        res.checks["train_fit"] = False
        return res
    err, fn, theta = best
    res.metrics["train_max_rel_err"] = err
    res.fitted_params = {n: float(v) for n, v in zip(param_names, theta)}
    res.checks["train_fit"] = err <= cfg.train_max_rel_err

    # 5. holdout transfer
    if holdout is not None:
        sys_dep = [i for i, n in enumerate(param_names) if params_spec[n].get("system_dependent")]
        fixed_idx = [i for i in range(len(param_names)) if i not in sys_dep]
        try:
            theta_h, r_h = _fit(fn, [holdout[n] for n in cfg.inputs], holdout[cfg.target],
                                len(param_names), fixed_idx, [theta[i] for i in fixed_idx],
                                list(theta), rng)
            herr = float(np.max(np.abs(np.expm1(r_h))))
            res.metrics["holdout_max_rel_err"] = herr
            res.holdout_params = {n: float(v) for n, v in zip(param_names, theta_h)}
            res.checks["holdout_transfer"] = herr <= cfg.holdout_max_rel_err
        except ValueError as e:
            res.checks["holdout_transfer"] = False
            res.errors.append(f"holdout fit: {e}")

    res.passed = all(res.checks.values())
    for k, v in list(res.metrics.items()):
        if isinstance(v, float) and not math.isfinite(v):
            res.metrics[k] = float("inf")
    return res
