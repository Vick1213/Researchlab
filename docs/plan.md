# Discovery Engine: Can an AI system produce results rather than mimic them?

Working plan and conversation notes. Written 2026-10-24.
Seed document for the repository; kept here as the reference for scope and intent.

---

## 1. The core question

Can an AI system arrive at a scientific result it was never shown, as opposed to
retrieving or paraphrasing one it saw in training?

The clean thought experiment: train a model only on pre-1905 text, hand it the
state of physics at the time, and see whether it produces special relativity.
We cannot run that at full strength (there is not enough pre-1905 text for a
frontier-scale model), but there are two practical substitutes:

1. Time-locked models trained on historical corpora (small, weak, but
   uncontaminated).
2. Modern models tested on results published after their knowledge cutoff
   (strong, and the cutoff is real rather than simulated).

## 2. What already exists (state of the field as of late Oct 2026)

### 2.1 Time-locked / historical language models
- TypewriterLM (arXiv 2606.02991): 7.24B model trained only on English text
  before 1913. 54B-token TypewriterCorpus with leakage mitigation.
- talkie-1930 (talkie-lm.com): 13B model, 260B tokens of pre-1931 English.
  Explicit goal is to test generalization beyond training data. Reports
  heavy problems with OCR quality and "temporal leaks" (later annotations
  contaminating old documents).
- history-llms (github DGoettlich): open project, models with 1913 and 1929
  cutoffs, 80B to 600B tokens.
- TimeCapsule (arXiv 2607.24750): 1.2B model on Victorian text 1800 to 1875.

Status: all are far too small to derive anything deep. Useful for humanities
and as a sanity check on scaffolding, not as a discovery engine.

### 2.2 Rediscovery benchmarks on modern models
- MOOSE-Chem (see LLM4SR survey, arXiv 2501.04306): LLM framework rediscovered
  main innovations of many 2024 Nature/Science chemistry and materials
  hypotheses using models with an Oct 2023 cutoff. Caveat: the right
  ingredients (background, inspiration papers) are largely handed over.
- FIRE-Bench (arXiv 2602.02905): agents rediscover findings from papers by
  writing and executing code. Contamination analysis found no consistent
  pre-cutoff advantage once difficulty is controlled.
- DBench-Bio (arXiv 2603.03322): dynamic benchmark from post-cutoff Q1
  biology abstracts. Frontier models score uniformly low.
- Inspiration-based hypothesis benchmark (arXiv 2503.21248): 2024-onward
  papers only, models recover ~80% of ground-truth inspirations early on.

### 2.3 Negative results worth remembering
- "Simulated Ignorance Fails" (arXiv 2601.13717): prompting a model to pretend
  it does not know post-date facts does not work. 52% gap between simulated
  and true ignorance. Do not use prompt-based cutoffs for evaluation.
- "Can Prompts Rewind Time for LLMs?" (arXiv 2510.02340): same conclusion.
- Memorization of economic data (arXiv 2504.14765): models recall exact
  pre-cutoff numbers; only post-cutoff evaluation is trustworthy.
- Vafa et al. 2025 (inductive bias / world models): a transformer trained on
  orbital data predicted orbits accurately but did not recover Newtonian
  mechanics. Prediction and discovery come apart.
- Self-correction / self-debate without external grounding has generally
  shown weak gains (e.g. Huang et al. 2023, "LLMs Cannot Self-Correct
  Reasoning Yet"). Fluency is the failure mode.

### 2.4 Positive results: genuine novel outputs
All come from a generate-many, verify-externally, keep-survivors loop:
- FunSearch (DeepMind 2023): new cap set constructions.
- AlphaEvolve (DeepMind 2025): improved 4x4 matrix multiplication over
  Strassen, improved bounds on several open problems.
- AlphaProof: IMO silver level on post-training problems.
- Agentic science systems: Google AI co-scientist, Sakana AI Scientist,
  FutureHouse agents. Early, mostly incremental.

Pattern: real discovery so far needs a cheap, external, non-LLM verifier.
Closer to Edison than Einstein.

## 3. Ideas developed in the conversation

### 3.1 Train the process, not the content
Reasoning-model RL (o1 / R1 style) already instills process behaviors
(decompose, check, backtrack) by rewarding verifiable answers. Extend the
same approach to the scientific method: hypothesize, test, update.

Bottleneck: the reward signal. Options, from strongest to weakest:
1. Simulators (physics, chemistry, some biology). Fast, faithful where they
   exist.
2. Rediscovery as reward: hide a known result, reward recovery.
3. LLM judge scoring the process. Weakest; rewards sounding rigorous. RL
   will find the gap.

### 3.2 Population search over assumptions
Humans failed to drop absolute time not from lack of talent but because
everyone searched from the same priors and questioning a shared axiom was
career-costly. Models have neither constraint.

Design: many instances, each assigned a different set of assumptions to hold
or drop. Lift FunSearch/AlphaEvolve population search from "programs" to
"axioms."

Filter: the correspondence principle. Any new theory must reproduce all
verified earlier results in the appropriate limit. Mechanical and checkable.
Dropping absolute time passes; dropping energy conservation fails fast.

Hard parts:
- Dangerous assumptions are implicit. Absolute time was not an axiom in
  1900 textbooks. Need an axiomatization step that makes the implicit
  explicit before varying it.
- Combinatorial assumption space. Must be steered by anomalies (Einstein
  was pushed by the Maxwell vs Galilean conflict and the Michelson-Morley
  null result, not searching at random).
- Lorentz had the right math by 1904 and kept the ether. Right formulas,
  wrong assumption. Simplicity under equal predictive power is a scorable
  tie-breaker.

### 3.3 Thought experiments as cheap verifiers
Einstein's thought experiments (light beam, elevator) cost nothing to run and
end in a checkable contradiction between well-verified constraints. They are
proofs by contradiction in narrative form. This partially solves the
reward-signal problem: consistency testing scales without a lab.

Discipline required: each soft simulation must terminate in either a formal
contradiction between stated premises or a derivation someone can check.
Otherwise it is storytelling, and LLMs are very good at convincing
storytelling.

## 4. The plan

### Phase 1: Discovery corpus (first deliverable)
Collect 50 to 100 cases, deliberately mixed in scale.

Major: special and general relativity, natural selection, plate tectonics,
DNA structure, germ theory, quantum hypothesis (Planck), periodic table,
oxygen / phlogiston, Copernican model, Maxwell's unification.

Minor: Balmer formula, Ohm's law, Boyle's law, Mendel's ratios, Kepler's laws
from Brahe's data, Snell's law, Hubble's law, Rutherford scattering,
blackbody fits, plus recent single-paper results (post-cutoff, from
FIRE-Bench / DBench-Bio style sources).

Decompose every case into one schema:
- knowledge_state_before: what was known and accepted at time T
- anomalies: known unexplained observations
- assumptions_explicit: stated axioms of the dominant theory
- assumptions_implicit: unstated shared beliefs (the hard part)
- the_move: what cracked it (see taxonomy below)
- verification: how it was confirmed, what data, how long
- dead_ends: what smart people tried and why it failed
- near_misses: people who had the pieces but not the conclusion (Lorentz)
- oracle_candidates: what could mechanically check a proposed answer

Move taxonomy (initial, to be refined from the cases):
- drop a shared assumption
- unify two theories that conflict at their boundary
- take a limiting case to the extreme
- transfer an analogy from another field
- exploit a symmetry or invariance
- trust the data over the theory (accept an anomaly as real)
- trust the theory over the data (reject an anomaly as artifact)
- change the question (reframe what needs explaining)
- new instrument or new data source

Sources to draw on: Kuhn (Structure of Scientific Revolutions), Holton
(Thematic Origins of Scientific Thought), Galison (Einstein's Clocks,
Poincare's Maps), Pais (Subtle is the Lord), Lakatos, primary papers where
accessible.

### Phase 2: Replay tasks
Each case becomes a task triple:
- knowledge pack: frozen snapshot of what was known (text + data)
- hidden target: the result
- oracle: non-LLM check. Data to fit, correspondence-principle limits,
  symbolic math (sympy / Lean where feasible), simulators.

Rule: no LLM judge in the oracle unless there is no alternative, and then
flag it.

### Phase 3: The system
Roles in a pipeline (each can be a separate agent or prompt):
1. Axiomatizer: reads the knowledge pack, outputs explicit and inferred
   implicit assumptions.
2. Anomaly collector: lists unexplained observations and conflicts between
   accepted theories.
3. Hypothesis population: N agents, each assigned an assumption subset to
   hold / drop, steered toward the anomalies.
4. Thought-experiment engine: must end in a formal contradiction or a
   derivation. Rejects outputs that end in prose.
5. Verifier: scores against the oracle (fit to data, limits recovered,
   math checks, simplicity).
6. Selection and memory: keep survivors, record lineage, feed back.

Later: RL over the whole loop with oracle score as reward. Process reward
only where an oracle exists; never LLM-judge-only RL.

### Phase 4: Evaluation ladder
1. Minor rediscoveries with cheap oracles (Kepler from Brahe tables, Balmer
   from spectral lines, Boyle from pressure-volume data).
2. Medium: special relativity from a pack containing Maxwell, Galilean
   mechanics, Michelson-Morley. Oracle: Lorentz invariance, Newtonian limit.
3. Post-cutoff recent papers (clean measurement of reasoning vs recall).
4. Open problems.

### The contamination problem (be honest about it)
Frontier models already know relativity. Historical replays cannot prove
reasoning over recall. Mitigations:
- Use historical cases primarily to build the taxonomy and as training data.
- Reserve clean measurement for post-cutoff minor results.
- Run a few marquee cases through a time-locked model (talkie-1930 or
  TypewriterLM) to test whether the scaffolding helps at all, accepting the
  base model is weak.
- Never rely on prompt-based "pretend you don't know" (see 2.3).

## 5. Open questions
- Can the axiomatizer actually surface implicit assumptions, or does it only
  list what textbooks already state? Test this on cases where we know the
  implicit assumption (absolute time, fixed continents, fixed species).
- How to score "simplicity" without hand-waving. Candidates: description
  length of the theory, number of free parameters, number of ad hoc fixes.
- Which simulators are good enough to serve as oracles? Start with classical
  mechanics and spectroscopy.
- How much of MOOSE-Chem's success is from being handed inspiration papers?
  Replicate with and without.
- Is there a minimum model scale below which process scaffolding does
  nothing? The time-locked models will tell us.

## 6. Suggested first tasks
1. Set up repo structure: /corpus (one YAML or JSON per case following the
   schema above), /tasks (knowledge pack + oracle per case), /engine
   (pipeline roles), /eval.
2. Write the case schema as a JSON schema and validate against it.
3. Research and fill 10 cases to start: 5 minor with cheap oracles (Kepler,
   Balmer, Boyle, Ohm, Mendel), 5 major (special relativity, general
   relativity, natural selection, plate tectonics, DNA structure).
4. Build the first oracle: Kepler's third law from synthetic or historical
   orbital data, checked by curve fit plus dimensional consistency.
5. Run a baseline: a plain frontier model given the Kepler knowledge pack,
   no scaffolding. Record what it does. Then add roles one at a time and
   measure the delta.
6. Pull FIRE-Bench and DBench-Bio task formats and see what can be reused.

## 7. References
- FIRE-Bench: https://arxiv.org/html/2602.02905
- Simulated Ignorance Fails: https://arxiv.org/html/2601.13717v1
- Can Prompts Rewind Time: https://arxiv.org/pdf/2510.02340
- Memorization Problem (economic forecasts): https://arxiv.org/html/2504.14765v1
- TypewriterLM: https://huggingface.co/papers/2606.02991
- talkie-1930: https://talkie-lm.com/introducing-talkie
- history-llms: https://github.com/DGoettlich/history-llms
- TimeCapsule: https://arxiv.org/pdf/2607.24750
- LLM4SR survey (MOOSE-Chem result): https://arxiv.org/html/2501.04306v1
- DBench-Bio: https://pith.science/paper/2603.03322
- Inspiration-based hypothesis benchmark: https://arxiv.org/pdf/2503.21248
- LLMLagBench: https://arxiv.org/pdf/2511.12116v1
- Data temporality in pretraining: https://arxiv.org/html/2605.22769v1
- Vafa et al. 2025, inductive bias / world models (orbital mechanics): search
  "What has a foundation model found? inductive bias world models"
- FunSearch, AlphaEvolve, AlphaProof: DeepMind blog posts and papers
