"""Model backends behind one interface.

Every backend turns a GenerationRequest into a Generation. Experiments name backends
with spec strings, e.g. ``anthropic:claude-opus-5-5?effort=high`` or
``replay:tests/fixtures/replies``. Register new backends (open-weight models served
locally, policies under RL training) with ``@register("name")``; see docs/backends.md.
"""
from engine.models.base import Backend, Generation, GenerationRequest, Message
from engine.models.registry import available, get_backend, parse_spec, register

# Import built-in backends so they register themselves.
from engine.models import anthropic_backend, offline  # noqa: E402,F401

__all__ = ["Backend", "Generation", "GenerationRequest", "Message",
           "available", "get_backend", "parse_spec", "register"]
