"""Prompt construction for replay tasks."""
from __future__ import annotations

import json
import re

from engine.tasks import Variant

ANSWER_FORMAT = """\
## How to answer

Reason however you like, then end your reply with exactly one fenced JSON block:

```json
{{
  "law": "<one equation using {symbols} and named constants, sympy syntax, one '='>",
  "parameters": {{
    "<constant>": {{
      "units": "<dimension of the constant in terms of length, time, mass; '1' if dimensionless>",
      "system_dependent": <true if the constant may differ for another system of bodies, else false>,
      "initial": <rough numerical value>
    }}
  }},
  "explanation": "<two or three sentences>"
}}
```

{target} has dimension {target_dim}; {inputs_desc}. Constants are fitted to the
data by least squares, so give their meaning and units, not precise values. Use as
few constants as you can (at most {max_params}). Exponents you are sure of should be
written as numbers, not as constants.
"""


def build(v: Variant) -> str:
    obs = v.spec["observables"]
    target = next(k for k, o in obs.items() if o["role"] == "target")
    inputs = [k for k, o in obs.items() if o["role"] == "input"]
    parts = [v.pack_text.rstrip(), ""]
    for path in v.visible_files():
        parts += [f"### {path.name}", "```csv", path.read_text().rstrip(), "```", ""]
    parts.append(ANSWER_FORMAT.format(
        symbols=", ".join([target, *inputs]),
        target=target,
        target_dim=obs[target]["dimension"],
        inputs_desc=", ".join(f"{i} has dimension {obs[i]['dimension']}" for i in inputs),
        max_params=v.oracle.get("thresholds", {}).get("max_params", 2),
    ))
    return "\n".join(parts)


def build_request(v: Variant, **options) -> "GenerationRequest":
    """Single-turn request for a task variant, tagged so offline backends can route it."""
    from engine.models import GenerationRequest, Message
    return GenerationRequest(messages=[Message("user", build(v))], options=options,
                             tags={"task": v.task_id, "variant": v.name})


_JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def extract_candidate(text: str) -> dict:
    """Return the last fenced JSON block in a model reply."""
    blocks = _JSON_BLOCK.findall(text)
    if not blocks:
        raise ValueError("no ```json block found in reply")
    return json.loads(blocks[-1])
