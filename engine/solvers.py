"""Solvers: strategies that use a backend to answer a task.

``baseline`` is one plain call. The pipeline roles from the plan (axiomatizer,
anomaly collector, hypothesis population, thought-experiment engine) will be added
as further solvers, so each can be compared against baseline on the same tasks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from engine import prompts
from engine.models import Backend, Generation, GenerationRequest
from engine.tasks import Variant


@dataclass
class Attempt:
    final_text: str
    calls: list[tuple[GenerationRequest, Generation]] = field(default_factory=list)

    def calls_as_dicts(self) -> list[dict]:
        return [{"request": r.to_dict(), "generation": g.to_dict()} for r, g in self.calls]


class Solver(Protocol):
    name: str

    def solve(self, v: Variant, backend: Backend, sample: int) -> Attempt: ...


_SOLVERS: dict[str, Callable[..., Solver]] = {}


def register(name: str):
    def deco(factory):
        _SOLVERS[name] = factory
        return factory
    return deco


def get_solver(name: str, **kwargs) -> Solver:
    if name not in _SOLVERS:
        raise KeyError(f"unknown solver {name!r}; registered: {sorted(_SOLVERS)}")
    return _SOLVERS[name](**kwargs)


@register("baseline")
class BaselineSolver:
    """One call with the knowledge pack and data; no scaffolding."""

    name = "baseline"

    def __init__(self, **request_options):
        self.request_options = request_options

    def solve(self, v: Variant, backend: Backend, sample: int) -> Attempt:
        req = prompts.build_request(v, **self.request_options)
        req.tags["sample"] = sample
        gen = backend.generate(req)
        return Attempt(final_text=gen.text, calls=[(req, gen)])
