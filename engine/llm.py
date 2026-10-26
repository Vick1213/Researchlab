"""Thin wrapper over the Anthropic Messages API."""
from __future__ import annotations

import anthropic

DEFAULT_MODEL = "claude-opus-5-5"


def complete(prompt: str, model: str = DEFAULT_MODEL, effort: str = "high",
             max_tokens: int = 64000) -> dict:
    """Single-turn call. Returns the reply text plus metadata for the run record.

    Refusal fallback is on ("default" routing); the record notes which model served.
    """
    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {msg.stop_details}")
    text = "".join(b.text for b in msg.content if b.type == "text")
    return {
        "text": text,
        "model_requested": model,
        "model_served": msg.model,
        "stop_reason": msg.stop_reason,
        "usage": {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens},
    }
