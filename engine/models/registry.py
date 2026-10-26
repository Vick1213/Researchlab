"""Backend registry and spec-string parsing.

Spec format: ``<backend>:<model>[?key=value&key=value]``. Query values are parsed as
int, float or bool where possible and passed to the backend as options.
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import parse_qsl

from engine.models.base import Backend

_REGISTRY: dict[str, type[Backend]] = {}


def register(name: str) -> Callable[[type[Backend]], type[Backend]]:
    def deco(cls: type[Backend]) -> type[Backend]:
        if name in _REGISTRY:
            raise ValueError(f"backend {name!r} already registered")
        cls.name = name
        _REGISTRY[name] = cls
        return cls
    return deco


def available() -> list[str]:
    return sorted(_REGISTRY)


def _coerce(value: str) -> Any:
    low = value.lower()
    if low in ("true", "false"):
        return low == "true"
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def parse_spec(spec: str) -> tuple[str, str, dict[str, Any]]:
    if ":" not in spec:
        raise ValueError(f"backend spec {spec!r} must look like '<backend>:<model>'")
    name, rest = spec.split(":", 1)
    model, _, query = rest.partition("?")
    return name, model, {k: _coerce(v) for k, v in parse_qsl(query)}


def get_backend(spec: str, **overrides: Any) -> Backend:
    name, model, options = parse_spec(spec)
    if name not in _REGISTRY:
        raise KeyError(f"unknown backend {name!r}; registered: {available()}")
    backend = _REGISTRY[name](model, **{**options, **overrides})
    backend._spec = spec
    return backend
