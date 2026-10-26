# eval

`python -m engine run <experiment.yaml>` writes `runs/<name>/<timestamp>/`:

- `manifest.json`: config, git commit and dirty flag, package versions, backend
  descriptions, the prompt hash per task variant, start and finish times.
- `records.jsonl`: one line per attempt with every model call (request and
  generation), the final reply, the parsed candidate, the oracle verdict and the reward.
- `summary.json`: pass rate, mean reward and error count per (backend, task, variant).

Commit run directories you want to keep as results; `smoke_replay/` is ignored.
