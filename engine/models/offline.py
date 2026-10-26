"""Backends that never run a model: for tests, dry runs and re-scoring saved replies."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from engine.models.base import Backend, Generation, GenerationRequest
from engine.models.registry import register


@register("replay")
class ReplayBackend(Backend):
    """Returns saved replies. ``model`` is a directory holding ``<task>__<variant>.md``
    files (or ``<task>__<variant>__<sample>.md`` for per-sample replies).
    """

    makes_model_calls = False

    def generate(self, request: GenerationRequest) -> Generation:
        d = Path(self.model)
        t = request.tags
        base = f"{t.get('task')}__{t.get('variant')}"
        for name in (f"{base}__{t.get('sample')}.md", f"{base}.md"):
            if (d / name).exists():
                return Generation(text=(d / name).read_text(), model_requested=None,
                                  model_served=f"replay:{d / name}", finish_reason="replay")
        raise FileNotFoundError(f"no saved reply for {base} in {d}")


@register("scripted")
class ScriptedBackend(Backend):
    """Returns whatever a Python callable returns. Construct directly in tests:
    ``ScriptedBackend("name", fn=lambda request: "...")``.
    """

    makes_model_calls = False

    def __init__(self, model: str = "scripted", fn: Callable[[GenerationRequest], str] | None = None, **options):
        super().__init__(model, **options)
        self.fn = fn or (lambda request: "")
        self.requests: list[GenerationRequest] = []

    def generate(self, request: GenerationRequest) -> Generation:
        self.requests.append(request)
        return Generation(text=self.fn(request), model_requested=self.model,
                          model_served=f"scripted:{self.model}", finish_reason="scripted")
