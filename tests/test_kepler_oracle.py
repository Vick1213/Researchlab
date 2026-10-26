import pytest

from engine import prompts, tasks
from oracles.dimensions import DimensionError, dimension_of, parse_units
import sympy as sp


def score(variant, law, params):
    return tasks.score(tasks.load("kepler_third_law", variant), {"law": law, "parameters": params})


K_SYS = {"k": {"units": "time**2/length**3", "system_dependent": True}}


def test_true_law_passes_historical():
    r = score("historical", "T**2 = k*a**3", K_SYS)
    assert r["passed"], r
    assert r["metrics"]["train_max_rel_err"] < 0.01
    assert r["metrics"]["holdout_max_rel_err"] < 0.01


def test_power_law_with_fitted_exponent_passes_and_recovers_three_halves():
    params = {"C": {"units": "time/length**p", "system_dependent": True},
              "p": {"units": "1", "system_dependent": False, "initial": 1.0}}
    r = score("historical", "T = C*a**p", params)
    assert r["passed"], r
    assert r["fitted_params"]["p"] == pytest.approx(1.5, abs=0.005)


def test_constant_not_marked_system_dependent_fails_transfer():
    params = {"k": {"units": "time**2/length**3", "system_dependent": False}}
    r = score("historical", "T**2 = k*a**3", params)
    assert r["checks"]["train_fit"] and not r["checks"]["holdout_transfer"]


def test_linear_law_fails():
    r = score("historical", "T = k*a", {"k": {"units": "time/length", "system_dependent": True}})
    assert not r["passed"] and not r["checks"]["train_fit"]


def test_recalled_kepler_fails_synthetic():
    r = score("synthetic", "T**2 = k*r**3", K_SYS)
    assert not r["checks"]["train_fit"], r


def test_true_synthetic_law_passes():
    r = score("synthetic", "T**4 = k*r**5", {"k": {"units": "time**4/length**5", "system_dependent": True}})
    assert r["passed"], r


def test_too_many_parameters_fails_parsimony():
    params = {n: {"units": "time/length**%d" % i, "system_dependent": True} for i, n in enumerate("bcd")}
    r = score("historical", "T = b + c*a + d*a**2", params)
    assert not r["checks"]["parsimony"]


def test_wrong_units_fail_dimension_check():
    r = score("historical", "T**2 = k*a**3", {"k": {"units": "time/length", "system_dependent": True}})
    assert not r["checks"]["dimensions"]


def test_adding_time_and_length_is_inhomogeneous():
    T, a = sp.symbols("T a", positive=True)
    dims = {T: parse_units("time"), a: parse_units("length")}
    with pytest.raises(DimensionError):
        dimension_of(T + a, dims)


def test_undeclared_symbol_rejected():
    r = score("historical", "T**2 = k*a**3*G", K_SYS)
    assert not r["checks"]["parse"]


def test_prompt_never_contains_hidden_data():
    for variant in ("historical", "synthetic"):
        v = tasks.load("kepler_third_law", variant)
        p = prompts.build(v)
        holdout = v.holdout_path.read_text().splitlines()[1]
        assert holdout.split(",")[0] not in p
        assert "hidden" not in p


def test_extract_candidate_takes_last_block():
    text = 'x\n```json\n{"law": "a=b"}\n```\nmore\n```json\n{"law": "T=k*a"}\n```'
    assert prompts.extract_candidate(text)["law"] == "T=k*a"
