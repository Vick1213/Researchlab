"""Offline tests for the experiment framework. No test here calls a model."""
import json

import pytest

from engine import experiment, rl, scoring, tasks
from engine.models import Backend, Generation, get_backend, parse_spec, register
from engine.models.offline import ScriptedBackend
from engine.models.registry import _REGISTRY

FIXTURES = tasks.ROOT / "tests" / "fixtures" / "replies"
GOOD_SYNTHETIC = (FIXTURES / "kepler_third_law__synthetic.md").read_text()
RECALLED_KEPLER = '```json\n{"law": "T**2 = k*r**3", "parameters": {"k": {"units": "time**2/length**3", "system_dependent": true}}}\n```'


def cfg(**kw):
    base = dict(name="t", tasks=["kepler_third_law:synthetic"], backends=["replay:" + str(FIXTURES)])
    return experiment.ExperimentConfig(**{**base, **kw})


def test_parse_spec_coerces_options():
    assert parse_spec("anthropic:claude-opus-5-5?effort=high&n=3&x=0.5&b=true") == (
        "anthropic", "claude-opus-5-5", {"effort": "high", "n": 3, "x": 0.5, "b": True})


def test_spec_keeps_options():
    assert get_backend("anthropic:claude-opus-5-5?effort=low").spec == "anthropic:claude-opus-5-5?effort=low"


def test_anthropic_backend_construction_makes_no_call():
    b = get_backend("anthropic:claude-opus-5-5")
    assert b.makes_model_calls and b._client is None


def test_runner_refuses_model_backends_without_flag(tmp_path):
    with pytest.raises(experiment.ModelCallsNotAllowed):
        experiment.run(cfg(backends=["anthropic:claude-opus-5-5"]), out_root=tmp_path)
    assert not any(tmp_path.iterdir())


def test_replay_run_writes_records_manifest_summary(tmp_path):
    out = experiment.run(cfg(tasks=["kepler_third_law:historical", "kepler_third_law:synthetic"]), out_root=tmp_path)
    recs = experiment.load_records(out)
    assert len(recs) == 2 and all(r["oracle"]["passed"] and r["reward"] == 1.0 for r in recs)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["n_records"] == 2 and "commit" in manifest["git"]
    summary = json.loads((out / "summary.json").read_text())
    assert {s["variant"] for s in summary} == {"historical", "synthetic"}


def test_scripted_backend_samples_and_mixed_rewards(tmp_path):
    replies = iter([GOOD_SYNTHETIC, RECALLED_KEPLER, "no json here"])
    b = ScriptedBackend("mix", fn=lambda req: next(replies))
    out = experiment.run(cfg(samples=3), out_root=tmp_path, backends=[b])
    recs = sorted(experiment.load_records(out), key=lambda r: r["sample"])
    assert [r["reward"] for r in recs] == [1.0, 0.0, 0.0]
    assert recs[2]["oracle"]["checks"] == {"extract": False}
    assert [r.tags["sample"] for r in b.requests] == [0, 1, 2]
    assert json.loads((out / "summary.json").read_text())[0]["pass_rate"] == pytest.approx(1 / 3)


def test_backend_exception_is_recorded_not_raised(tmp_path):
    def boom(req):
        raise RuntimeError("server down")
    out = experiment.run(cfg(), out_root=tmp_path, backends=[ScriptedBackend("boom", fn=boom)])
    (rec,) = experiment.load_records(out)
    assert rec["error"] == "RuntimeError: server down" and rec["reward"] == 0.0


def test_prompt_sent_to_backend_has_no_hidden_data(tmp_path):
    b = ScriptedBackend("spy", fn=lambda req: "")
    experiment.run(cfg(), out_root=tmp_path, backends=[b])
    text = b.requests[0].messages[0].content
    assert "B-1" not in text and "hidden" not in text


def test_shaped_reward_gives_partial_credit():
    v = tasks.load("kepler_third_law", "synthetic")
    _, oracle = scoring.score_reply(v, RECALLED_KEPLER)
    assert scoring.reward(oracle, "binary") == 0.0
    assert 0.0 < scoring.reward(oracle, "shaped") < 0.5


def test_task_env_and_reward_fn():
    env = rl.TaskEnv("kepler_third_law", "synthetic")
    assert env.reset()[0]["role"] == "user"
    assert env.step(GOOD_SYNTHETIC).reward == 1.0
    conv = [{"role": "assistant", "content": GOOD_SYNTHETIC}]
    rewards = rl.reward_fn(prompts=[None, None], completions=[conv, RECALLED_KEPLER],
                           task=["kepler_third_law"] * 2, variant=["synthetic"] * 2, extra_column=[1, 2])
    assert rewards == [1.0, 0.0]


def test_exports(tmp_path):
    n = rl.export_prompt_dataset(["kepler_third_law:synthetic"], tmp_path / "p.jsonl", repeats=3)
    assert n == 3
    row = json.loads((tmp_path / "p.jsonl").read_text().splitlines()[0])
    assert row["task"] == "kepler_third_law" and row["prompt"][0]["role"] == "user"

    replies = iter([GOOD_SYNTHETIC, RECALLED_KEPLER])
    out = experiment.run(cfg(samples=2), out_root=tmp_path / "runs",
                         backends=[ScriptedBackend("m", fn=lambda r: next(replies))])
    assert rl.export_trajectories([out], tmp_path / "all.jsonl") == 2
    assert rl.export_trajectories([out], tmp_path / "good.jsonl", min_reward=1.0) == 1
    good = json.loads((tmp_path / "good.jsonl").read_text())
    assert good["completion"][0]["content"] == GOOD_SYNTHETIC and good["passed"]


def test_custom_backend_registration(tmp_path):
    @register("unit_test_echo")
    class Echo(Backend):
        makes_model_calls = False

        def generate(self, request):
            return Generation(text=GOOD_SYNTHETIC, model_requested=self.model, model_served=self.model)

    try:
        out = experiment.run(cfg(backends=["unit_test_echo:m1?temperature=0.7"]), out_root=tmp_path)
        (rec,) = experiment.load_records(out)
        assert rec["backend"] == "unit_test_echo:m1?temperature=0.7" and rec["reward"] == 1.0
    finally:
        _REGISTRY.pop("unit_test_echo")
