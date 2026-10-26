"""Minimal dimensional analysis over sympy expressions.

A dimension is a dict mapping base dimension name -> exponent. Exponents are sympy
expressions, so a fitted exponent such as ``a**p`` is allowed when the declared
units of the accompanying constant also mention ``p`` (e.g. ``time/length**p``).
"""
from __future__ import annotations

import sympy as sp

BASE = ("length", "time", "mass", "current", "temperature", "amount")
_BASE_SYMBOLS = {name: sp.Symbol(name, positive=True) for name in BASE}


class DimensionError(ValueError):
    pass


def parse_units(text: str, param_symbols: dict[str, sp.Symbol] | None = None) -> dict:
    """Parse a units string like ``time**2/length**3`` or ``1`` into a dimension dict."""
    local = dict(_BASE_SYMBOLS)
    local.update(param_symbols or {})
    expr = sp.sympify(text, locals=local)
    out: dict = {}
    for base, exp in _powers(expr).items():
        if base == 1:
            continue
        if base not in _BASE_SYMBOLS.values():
            raise DimensionError(f"unknown base dimension {base} in units {text!r}")
        out[str(base)] = out.get(str(base), 0) + exp
    return _clean(out)


def _powers(expr: sp.Expr) -> dict:
    result: dict = {}
    for factor in sp.Mul.make_args(expr):
        if factor.is_number:
            continue
        base, exp = factor.as_base_exp()
        result[base] = result.get(base, 0) + exp
    return result


def _clean(d: dict) -> dict:
    return {k: sp.simplify(v) for k, v in d.items() if sp.simplify(v) != 0}


def same(a: dict, b: dict) -> bool:
    keys = set(a) | set(b)
    return all(sp.simplify(a.get(k, 0) - b.get(k, 0)) == 0 for k in keys)


def dimension_of(expr: sp.Expr, dims: dict[sp.Symbol, dict]) -> dict:
    """Return the dimension of ``expr`` or raise DimensionError if it is inhomogeneous."""
    if expr.is_Symbol:
        if expr not in dims:
            raise DimensionError(f"no dimension declared for symbol {expr}")
        return dims[expr]
    if expr.is_number:
        return {}
    if expr.is_Add:
        first = dimension_of(expr.args[0], dims)
        for term in expr.args[1:]:
            d = dimension_of(term, dims)
            if not same(first, d):
                raise DimensionError(f"adding terms with different dimensions: {expr.args[0]} vs {term}")
        return first
    if expr.is_Mul:
        out: dict = {}
        for factor in expr.args:
            for k, v in dimension_of(factor, dims).items():
                out[k] = out.get(k, 0) + v
        return _clean(out)
    if expr.is_Pow:
        base, exp = expr.args
        if dimension_of(exp, dims):
            raise DimensionError(f"exponent {exp} is not dimensionless")
        return _clean({k: v * exp for k, v in dimension_of(base, dims).items()})
    if isinstance(expr, sp.Function):
        for arg in expr.args:
            if dimension_of(arg, dims):
                raise DimensionError(f"argument of {expr.func} is not dimensionless: {arg}")
        return {}
    raise DimensionError(f"cannot assign a dimension to {expr!r}")
