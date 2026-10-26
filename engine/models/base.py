"""Backend interface shared by API models, local open-weight models and test doubles."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class GenerationRequest:
    messages: list[Message]
    system: str | None = None
    max_tokens: int = 64000
    # Backend-specific settings (effort, temperature, top_p, seed, ...). Each backend
    # reads the keys it understands and ignores the rest; the run record keeps them all.
    options: dict[str, Any] = field(default_factory=dict)
    # Free-form labels that let offline backends route a request (task, variant, sample).
    tags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Generation:
    text: str
    model_requested: str | None
    model_served: str | None
    finish_reason: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    latency_s: float | None = None
    # Anything else a backend can provide: token ids and logprobs from an open-weight
    # model (needed for on-policy RL), thinking summaries, fallback notices, etc.
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class Backend(ABC):
    """A model that answers requests.

    Subclasses set ``makes_model_calls`` to False only if they never run a model
    (replay, scripted). The experiment runner refuses backends with True unless
    model calls are explicitly allowed.
    """

    name: str = "base"
    makes_model_calls: bool = True

    def __init__(self, model: str, **options: Any):
        self.model = model
        self.options = options

    @property
    def spec(self) -> str:
        """The spec string this backend was built from, options included."""
        return getattr(self, "_spec", None) or f"{self.name}:{self.model}"

    @abstractmethod
    def generate(self, request: GenerationRequest) -> Generation:
        ...

    def describe(self) -> dict:
        """Recorded in the run manifest."""
        return {"spec": self.spec, "model": self.model, "options": self.options,
                "makes_model_calls": self.makes_model_calls}
