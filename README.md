# Researchlab: Discovery Engine

Can an AI system arrive at a scientific result it was never shown, rather than
retrieve one it saw in training? The full plan is in [docs/plan.md](docs/plan.md).

The approach: decompose historical and post-cutoff discoveries into a fixed schema,
turn each into a replay task (knowledge pack, hidden target, non-LLM oracle), then
measure a plain model against a pipeline of roles (axiomatizer, anomaly collector,
hypothesis population, thought-experiment engine, verifier) added one at a time.

## Layout

```
corpus/
  schema/case.schema.json   JSON schema every case follows
  cases/<id>.yaml           one discovery per file (filename == id)
tasks/<id>/
  task.yaml                 oracle config and variants
  pack_<variant>.md         knowledge pack shown to the solver
  data/                     data shown to the solver
  hidden/                   held-out data and ground truth, never put in a prompt
oracles/                    non-LLM checkers (law_fit.py, dimensions.py)
engine/                     task loading, prompts, API client, baseline runner
eval/runs/                  one JSON record per model run
docs/                       plan, benchmark-format survey
tools/validate_corpus.py    schema validation for the corpus
tests/                      oracle and corpus tests
```

## Quick start

```bash
pip install -e '.[dev]'
python tools/validate_corpus.py                                # validate all cases
python -m pytest                                               # oracle + corpus tests
python -m engine.baseline kepler_third_law synthetic --print-prompt
ANTHROPIC_API_KEY=... python -m engine.baseline kepler_third_law synthetic
python -m engine.baseline kepler_third_law historical --response-file reply.md --tag manual
```

## Status

| Step (plan section 6) | State |
| --- | --- |
| 1. Repo structure | done |
| 2. Case JSON schema + validator | done |
| 3. First 10 cases | written; see each file's `open_issues` for unverified claims |
| 4. Kepler oracle | done: fit, held-out transfer, parsimony, dimensional homogeneity |
| 5. Baseline | harness done; only proxy runs so far (no API key in the build session) |
| 6. FIRE-Bench / DBench-Bio formats | survey in [docs/benchmark_formats.md](docs/benchmark_formats.md) |

### The Kepler oracle

`oracles/law_fit.py` takes a candidate law such as `T**2 = k*a**3` with declared
units for each constant and checks, without any LLM:

1. it parses and can be solved for the target observable;
2. it has at most `max_params` free constants;
3. both sides have the same dimension (weak alone: a free constant can absorb any
   units, but it rejects sums of time and length and `exp(a)` of a dimensional `a`);
4. fitted in log space, it matches the training data (max relative error 2%);
5. on a held-out system, refitting only constants marked `system_dependent`, it
   still fits (5%). This is the "law, not curve fit" check.

Two variants:
- `historical`: six planets, held out Galilean moons. Contamination is total.
- `synthetic`: a fictional system with `T ∝ r^1.25`, so recalling 3/2 fails
  (recalled `T**2 = k*r**3` misses by 49%).

### First baseline result (proxy, not an API run)

Both variants passed: the historical one with `T**2 = k*a**3`, and the synthetic
one with `T = k*r**(5/4)`, which the model read off the data in a few log-ratio
steps and checked on the other bodies. Records are in `eval/runs/`.

What this shows: a one-variable power law with clean data is too easy to tell
scaffolding apart from a plain model. It is a smoke test for the harness, not a
benchmark. Harder obfuscated variants are needed before adding pipeline roles:
- forms that are not power laws (Balmer-type `1/n^2 - 1/m^2`, Planck-type
  `x^3/(e^x - 1)`), where the search space of forms is the difficulty;
- several candidate input columns, some irrelevant, so variable selection matters;
- heavier noise or sparse data, where parsimony decides between fits;
- tasks where the data contradict a stated prior theory in the pack (anomaly
  handling), which is closer to the "drop an assumption" move the project is about.

## Ground rules

- No LLM judge in an oracle unless there is no alternative; set `llm_free: false`
  when there is one.
- No prompt-based "pretend you don't know" cutoffs (see plan section 2.3).
- Nothing under `tasks/*/hidden/` goes into a prompt (`tests/` checks this).
- Historical claims carry a `confidence` field; anything unverified goes in
  `open_issues`.
