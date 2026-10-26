# Model backends and RL hooks

Everything that talks to a model goes through `engine.models.Backend`. A solver builds
`GenerationRequest`s, a backend returns `Generation`s, the oracle scores the final
reply, and `engine.scoring.reward` turns the verdict into a scalar. Swapping Claude for
an open-weight model changes only the backend spec in the experiment YAML.

## Built-in backends

| Spec | Runs a model | Use |
| --- | --- | --- |
| `anthropic:<model>?effort=high` | yes | Claude via the Messages API (needs `ANTHROPIC_API_KEY`) |
| `replay:<dir>` | no | re-score saved replies named `<task>__<variant>[__<sample>].md` |
| `scripted:<name>` | no | tests; construct `ScriptedBackend(fn=...)` in Python |

`python -m engine run` refuses any backend with `makes_model_calls = True` unless
`--allow-model-calls` is passed.

## Adding an open-weight backend

Subclass `Backend`, implement `generate`, register it under a name. Options from the
spec's query string arrive as `self.options`; per-request options override them.

```python
# engine/models/my_backend.py, then import it in engine/models/__init__.py
from engine.models import Backend, Generation, GenerationRequest, register


@register("vllm")
class VLLMBackend(Backend):
    """Spec: vllm:<model>?base_url=http://localhost:8000/v1&temperature=0.7"""

    def generate(self, request: GenerationRequest) -> Generation:
        opts = {**self.options, **request.options}
        ...  # call your server or local model here
        return Generation(
            text=text,
            model_requested=self.model,
            model_served=self.model,
            finish_reason=finish_reason,
            usage={"input_tokens": n_in, "output_tokens": n_out},
            # For on-policy RL, keep what the trainer needs:
            extra={"token_ids": ids, "logprobs": logprobs},
        )
```

Notes for local models:
- `request.system` and `request.messages` are role/content pairs; apply your model's
  chat template.
- `request.max_tokens` defaults to 64000, which is far above what most local models
  need. Set `max_tokens` per backend or per solver.
- Seeds and sampling settings belong in `options`; the run manifest records them.
- The run record stores `Generation.extra` verbatim, so large logprob arrays make
  large `records.jsonl` files. Drop them in `generate` if you only need text.

## Driving a live policy during training

`engine.experiment.run(cfg, backends=[...])` accepts constructed backends, so a
training loop can wrap its current policy in a `Backend` and run an evaluation
experiment in-process at each checkpoint, without a server.

## RL hooks (`engine/rl.py`)

- `TaskEnv(task, variant)`: `reset()` returns the prompt messages; `step(completion)`
  returns reward, oracle verdict and parsed candidate.
- `reward_fn(prompts, completions, task, variant, **kw)`: batch reward with the
  signature TRL's GRPOTrainer expects of a reward function, where `task` and
  `variant` are dataset columns. Untested against TRL itself.
- `python -m engine export-prompts out.jsonl kepler_third_law:synthetic --repeats 64`:
  a prompt dataset in conversational format with `task`/`variant` columns.
- `python -m engine export-trajectories out.jsonl eval/runs/<exp>/<ts> --min-reward 1`:
  scored (prompt, completion, reward) rows from finished runs, for rejection-sampling
  fine-tuning or offline RL.

Reward schemes (`engine/scoring.py`):
- `binary` (default): 1 if every oracle check passes, else 0.
- `shaped`: weighted partial credit per check (holdout transfer weighs most). Expect
  RL to exploit partial credit; use it for analysis or curriculum, not as the only
  training signal.
- `complexity_penalty`: subtracts `penalty * complexity` from a positive reward
  (parsimony pressure).

## Before training on these tasks

- The historical variants are contaminated: rewarding them rewards recall. Train on
  synthetic variants; keep historical and post-cutoff tasks for evaluation only.
- One Kepler task is not a training set. A procedural generator of synthetic law
  tasks (random forms, exponents, noise, distractor columns) is the next piece needed
  for RL; `tasks/kepler_third_law/make_synthetic.py` is the seed for it.
- The oracle reads `hidden/` data to compute the reward. That is fine as long as
  nothing in `hidden/` reaches the policy's context; `tests/` checks the prompt side.
