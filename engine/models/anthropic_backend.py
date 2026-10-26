"""Anthropic Messages API backend."""
from __future__ import annotations

import time

from engine.models.base import Backend, Generation, GenerationRequest
from engine.models.registry import register


@register("anthropic")
class AnthropicBackend(Backend):
    """Options: ``effort`` (low|medium|high|xhigh|max, default high) and
    ``fallbacks`` (default "default": server-side refusal fallback; set "off" to
    disable). Adaptive thinking is always on. Sampling options such as temperature
    are not sent: current Claude models reject them.
    """

    def __init__(self, model: str = "claude-opus-5-5", **options):
        super().__init__(model or "claude-opus-5-5", **options)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic  # imported lazily so offline use needs no SDK or key
            self._client = anthropic.Anthropic()
        return self._client

    def generate(self, request: GenerationRequest) -> Generation:
        opts = {**self.options, **request.options}
        kwargs = dict(
            model=self.model,
            max_tokens=request.max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": opts.get("effort", "high")},
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
        )
        if request.system:
            kwargs["system"] = request.system
        if opts.get("fallbacks", "default") != "off":
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"

        start = time.monotonic()
        with self.client.beta.messages.stream(**kwargs) as stream:
            msg = stream.get_final_message()
        latency = time.monotonic() - start

        text = "".join(b.text for b in msg.content if b.type == "text")
        extra = {}
        if msg.stop_reason == "refusal":
            extra["stop_details"] = str(msg.stop_details)
        return Generation(
            text=text,
            model_requested=self.model,
            model_served=msg.model,
            finish_reason=msg.stop_reason,
            usage={"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens},
            latency_s=latency,
            extra=extra,
        )
