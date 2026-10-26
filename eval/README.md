# eval

`runs/` holds one JSON record per model run: task, variant, condition, model (requested
and served), prompt hash, the full reply, the extracted candidate, and the oracle result.

Conditions so far:
- `baseline`: one plain model call on the knowledge pack, no scaffolding
  (`python -m engine.baseline <task> <variant>`).

Planned: add pipeline roles (axiomatizer, anomaly collector, hypothesis population,
thought-experiment engine) one at a time and record the delta against baseline on
the same tasks.

Runs tagged `subagent-proxy` were produced by a Claude Code subagent restricted to
reading the prompt and answering without tools, because the session that produced
them had no API key. They are not API runs: model settings (effort, system prompt)
differ, so treat them as indicative only and re-run with the API.
