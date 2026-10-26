# Task formats in existing rediscovery benchmarks

Research notes for the `/tasks` format. Each of our tasks has three parts: a knowledge
pack (a frozen snapshot of what was known, as text plus data), a hidden target, and an
oracle that checks answers without an LLM. These notes look at five benchmarks to see
which of their task formats we can reuse.

Compiled 2026-10-26.

## How the sources were accessed (read this first)

- **Every URL in the brief failed to load.** That includes arxiv.org (html/abs/pdf),
  pith.science, proceedings.mlr.press, papers.cool, firebench.github.io and the LLMLagBench
  HF Space. WebFetch failed DNS resolution for every host, and the session's egress proxy
  refused arxiv.org and huggingface.co (HTTP 403 on CONNECT). **No arXiv page was read
  directly.**
- Cloning public GitHub repos with git did work, so most statements below come from
  **the actual repo files** at these commits:
  - `maitrix-org/FIRE-Bench` @ a7017c9 (2026-04-28)
  - `firebench/firebench.github.io` @ HEAD. This repo bundles `static/FIRE_Bench.pdf`, the
    full paper, which I read with pdftotext.
  - `transcend-0/DBench-Bio` @ 82162e8 (2026-06-02)
  - `ZonglinY/MOOSE-Chem` @ f8cda98 (2025-11-12)
  - `ankitala/ResearchBench` @ 03873e0 (2026-06-01). This is the code release for arXiv
    2503.21248.
- **HuggingFace datasets could not be read** (proxy refused). This affects the full FIRE-Bench
  and ResearchBench task files and their dataset cards. For ResearchBench, the repo's
  `data/tiny/*.jsonl` split uses the same schema.
- The other paper-level facts (DBench-Bio abstract, LLMLagBench, ResearchBench, MOOSE-Chem
  paper text) come from **web-search result summaries only**. They are marked
  *[search-snippet]* and should be treated as lower confidence.
- **LLM4SR survey (arXiv 2501.04306): not read.** It was blocked, and search returned only its
  abstract. My MOOSE-Chem notes come from the MOOSE-Chem repo itself.

---

## 1. FIRE-Bench (arXiv 2602.02905, ICML 2026)

Agents get a research question from a published empirical LLM-behaviour paper. They write and
run code, and their written conclusions are compared with the paper's findings.

### 1.1 What one task contains
These come from the repo layout and README schema. Each task is a directory
`benchmark/papers/<task_id>/`. There are 35 "verified" (hand-curated) tasks and 153
"unverified" ones under `benchmark/papers_unverified/`. The unverified tasks were generated
automatically by the Paper2Bench pipeline with no human review, and each has
`STATUS = unverified`.

| File / field | Content | Shown to agent? |
|---|---|---|
| `task_id` | e.g. `lost_in_the_middle`, `inverse_scaling_rq0` | yes |
| `research_question` | one question | yes |
| `instruction/instruction.txt` | full prompt: question, models available, API-call budget, dataset description with a JSON schema example, experimental constraints (metric, sample counts) | yes |
| `instruction/instruction_gt.txt` | ground-truth procedural plan (what the paper did) | **no**, used by the evaluator |
| `conclusion.txt` | ground-truth finding, usually 1-3 sentences | **no** |
| `data/` | bundled data, present for 15 of 35 verified tasks (e.g. NQ-open JSONL files with the gold passage at each position) | yes |
| `dataset.txt` | pointer to an upstream source when data is not bundled (8 of 35) | yes |
| `task_config.yaml` | unverified tasks only: `paper_type`, `models.api/huggingface`, `budget_per_model`, `datasets[{name,source,description}]`, `constraints` (e.g. "Do NOT use web search") | partly |

The HF rows (`silence-suzuki/FIRE-Bench-verified`, `-unverified`) are said to carry `task_id`,
`research_question`, `instruction`, `instruction_gt` and `conclusion`. Verified rows add
`dataset_source` and `has_local_data`; unverified rows add `paper_type` and `task_config`.
*This is from the README; I could not open HF to check.*

Real example (`lost_in_the_middle`):
- Instruction: *"How does Large Language Model performance vary based on relevant information
  position in context?"* Resources: gpt-3.5-turbo, claude-1.3, mpt-30b-instruct and
  longchat-13b-16k, with a budget of 5000 calls per model. Data: `qa_data` multi-doc QA
  JSONL. Constraints: Exact Match, 50 samples per position across 20 positions.
- `conclusion.txt`: *"Large Language Model performance is better when relevant information is
  positioned at the very beginning or end of the input context, and it degrades significantly
  when the information is located in the middle."*
- `dataset.txt`: `https://github.com/nelson-liu/lost-in-the-middle`

### 1.2 Scoring
Scoring uses **an LLM judge throughout**. It follows RAGChecker: the agent's conclusion and the
ground-truth text are both split into atomic claims by an LLM. Each agent claim is then matched
to the ground-truth claims by an LLM entailment classifier, and the benchmark reports
claim-level Precision, Recall and F1. The paper names gpt-5.2 as the extractor and judge.
`eval/RAGChecker/eval.py` sets `eval_model = "gpt-5.2"` but also passes `openai/gpt-4.1` as
extractor/checker to RAGChecker, so the judge model is not pinned consistently in the code.
The paper validates the judge against humans in its Appendix E, which I did not read in detail.
Best reported result is about 47 F1 (Claude Code with Sonnet-4).

### 1.3 Contamination / cutoff
- Source papers come from ICLR/ICML/NeurIPS 2024-2025. The paper text says 30 papers; the
  repo has 35 verified tasks.
- There is no hard cutoff filter. Instead, Section 5.4 checks for contamination after the fact:
  tasks are split by publication date relative to each model's cutoff (o4-mini 2024-06-01,
  gpt-5 2024-09-30) and stratified by difficulty. The authors found "no strong evidence of
  systematic contamination" and say themselves that the analysis is coarse.
- Leakage of the answer through web search is handled only by an instruction ("Do NOT use web
  search") plus inspecting trajectories afterwards. Nothing enforces it.

### 1.4 License / location
- Code: GitHub `maitrix-org/FIRE-Bench`. **There is no LICENSE file at the repo root and none
  is mentioned in the README** (the vendored `eval/RAGChecker` is Apache-2.0). Ask the authors
  before redistributing.
- Data: HF `silence-suzuki/FIRE-Bench-verified` and `-unverified`, which are also mirrored in
  the repo under `benchmark/`. The HF license is **unverified** because HF was blocked.
- The repo also commits a `.env` file at the root (README says it holds API keys; contents not
  inspected).

### 1.5 Reuse for our schema
- **Reusable:**
  - The split between `instruction.txt` (shown) and `instruction_gt.txt` plus `conclusion.txt`
    (hidden) maps directly onto pack and hidden target.
  - Explicit resource budgets (API calls per model) and `constraints` lists in
    `task_config.yaml`.
  - A `data/` folder or a `dataset.txt` pointer for upstream data that is too large to bundle.
  - Directory-per-task layout, similar to ours.
  - The `verified` / `unverified` provenance flag.
- **Does not fit:**
  - The target is a prose claim and the oracle is an LLM entailment judge. Nothing is checked
    mechanically, even when the claim is quantitative (e.g. U-shaped accuracy versus position).
  - The knowledge pack is not a historical snapshot. It is just "here are the models and
    data", and the domain is ML-on-LLMs only.
  - Contamination is handled by statistics after the fact, not prevented by construction.
- We could add a mechanical oracle ourselves for the subset whose conclusions are directional
  or numeric over bundled data (e.g. lost-in-the-middle: check that accuracy at the edges
  exceeds accuracy in the middle).

---

## 2. DBench-Bio (arXiv 2603.03322)

This is a dynamic, monthly benchmark built from PubMed abstracts published after the model's
cutoff. Paper title from search: "Can Large Language Models Derive New Knowledge? A Dynamic
Benchmark for Biological Knowledge Discovery" (Chaoqun Yang et al., submitted 2026-02-10)
*[search-snippet]*. **pith.science and arXiv both failed to load**, so the paper itself was not
read. Everything below comes from the repo code.

### 2.1 What one task contains
- **The repo releases no task data**, only the pipeline. Running `benchmark.py` for a
  `year_month` (default `"202601"`) produces CSV rows with columns
  `title, abstract, question, answer` (`gen_AbstractQA.py`). It also adds filter scores
  `relevance`, `clarity` and `centrality`, which are 1-5 values from an LLM.
- Steps:
  1. `paper_abstract_download_Entrez.py` queries PubMed by date range and a journal list
     (`JCR_Biology_Biochemistry.csv`, i.e. JCR Q1 journals by category).
  2. An LLM turns each abstract into one QA pair.
  3. Rows are kept if `relevance >= 4`, `clarity >= 5` and `centrality >= 5`.
  4. The surviving rows are merged into `all.csv`.
- Real example. This is the few-shot example in `prompt.py`, not a released row:
  - question: *"Is there any mechanistic difference between RAS-induced autophagy and
    physiological autophagy?"*
  - answer: a 4-bullet list (non-canonical autophagy; PI4KB replaces class III PI3K;
    P38-ULK1-PI4KB-WIPI2 cascade with phosphorylation at S256/T263; multivesicular ATG8-labelled
    structures).
- The prompt tells the generator to avoid "specific parameters or numerical values". Answers
  are therefore qualitative by design.

### 2.2 Scoring
Scoring is **an LLM judge** (`eval/qa_eval_LLMJudge.py`), which gives a 1-5 score of the
candidate against the reference answer. There is also a ROUGE baseline (`qa_eval_baseline_H.py`
uses `evaluate.load("rouge")`), which is mechanical but only measures lexical overlap. The
README says scores are low overall, with a maximum of 5.

### 2.3 Contamination / cutoff
Contamination is handled by **time**: only abstracts published after the model's cutoff are
used, and a new set is built each month. This avoids the problem by construction, as long as
the month is after the cutoff. The README also contrasts the results with MMLU-Pro Biology and
argues that static benchmarks are inflated.

### 2.4 License / location
- GitHub `transcend-0/DBench-Bio`. **No LICENSE file in the repo.** The benchmark CSVs are not
  in the repo, and I found no HF dataset.
- Abstracts are under PubMed/publisher terms.

### 2.5 Reuse for our schema
- **Reusable:**
  - The idea of a rolling, date-stamped task set with "published after cutoff" as a field.
  - The automatic filter stages (relevance / clarity / centrality), which could be adapted as
    a triage step for candidate tasks.
- **Does not fit:**
  - There is no knowledge pack: the model gets only a question and must rely on what it has
    memorised.
  - There is no data, so no data-fit oracle is possible.
  - Answers are qualitative mechanism bullets checked by an LLM.
  - Post-cutoff biology findings can't be checked by a simulator or data fit.
- Overall this is a contamination strategy we could borrow (a `published_after` field per
  task), not a task format.

---

## 3. ResearchBench, the inspiration-based hypothesis benchmark (arXiv 2503.21248, Findings of ACL 2026)

Liu, Yang et al. "ResearchBench: Benchmarking LLMs in Scientific Discovery via
Inspiration-Based Task Decomposition". The arXiv PDF failed to load. The schema below comes from
the code release `ankitala/ResearchBench` and its `data/tiny/*.jsonl`.

### 3.1 What one task contains
The README says the full release has 1,369 paper records, 1,367 retrieval tasks, 1,367
generation tasks and 1,323 ranking tasks, across 12 disciplines. There are four JSONL files:

- `papers.jsonl` holds the decomposed paper. Fields: `sample_id`, `doi`, `discipline`,
  `title`, `abstract`, `research_question`, `background_survey`,
  `inspirations[{title, abstract, insp, relation}]`, `main_hypothesis`,
  `fine_grained_hypothesis` and `experiments_details`.
- `retrieve.jsonl` holds inspiration retrieval tasks. Fields: `research_question`,
  `background_survey`, `candidates[{index, title, abstract, label}]`, `gold_titles`,
  `label_counts` and `default_params`.
  - There are 75 candidates. Labels are `gold` (2-3) plus 24 each of `negative_t1`,
    `negative_t2` and `negative_t3`, which are graded hard negatives (same topic, same
    discipline, other).
- `generation.jsonl` holds hypothesis composition tasks. Fields: `research_question`,
  `background_survey`, `gold_inspirations[{title, abstract}]`, `gold_hypothesis`,
  `fine_grained_hypothesis`, `experiments_details` and `default_params`.
- `ranking.jsonl` holds hypothesis ranking tasks. Fields: `gold_hypothesis`,
  `fake_negative_hypotheses[]`, `model_negative_hypotheses[]` and `source_variant`.

Real example (tiny split, `Astronomy/101007s00159024001512`, DOI 10.1007/s00159-024-00151-2):
- RQ: *"What are the processes and sources responsible for the formation and evolution of dust in
  the early universe, particularly at redshifts greater than 4?"*
- Gold inspirations: "Dust formation in primordial Type II supernovae"; "Composition and
  quantities of dust produced by AGB-stars..."; "The evolution of refractory interstellar grains
  in the solar neighborhood".
- Quality note: this sample is a review article. Its `background_survey` begins with "Certainly!
  Here's a more concise version...", which is unedited LLM output. Extraction was automatic; the
  paper reports 91.9% / 82.3% decomposition accuracy on 62 expert-checked papers
  *[search-snippet]*.

### 3.2 Scoring
- **Retrieval: mechanical.** The score is the hit ratio of gold candidates among the selected
  titles, matched by fuzzy title similarity with a 0.62 threshold (`score_retrieve`).
- **Ranking: mechanical.** The score is pairwise accuracy of preferring the gold hypothesis,
  measured in both presentation orders.
- **Composition: an LLM judge.** It gives a "matched score" Likert rating of the generated
  hypothesis against `gold_hypothesis` and its key points (`score_generation`, judge
  temperature 0).

### 3.3 Contamination / cutoff
Source papers are from 2024 onward, chosen to limit overlap with pretraining
*[search-snippet + README]*. The retrieval task is described as out-of-distribution because the
gold link between papers is new. There is no per-model cutoff check in the code that I saw.

### 3.4 License / location
- Code: MIT.
- Data: **CC BY-NC 4.0** (`DATA_LICENSE.md`), and the file warns that abstracts are subject to
  publisher terms.
- Full data on HF `ankilok/ResearchBench` (not opened); a 12-sample tiny split is on GitHub.

### 3.5 Reuse for our schema
- **Reusable:**
  - The `inspirations[{title, abstract, relation}]` structure. It is a good model for the
    *literature part of a knowledge pack*: the prior papers that make the discovery reachable.
  - The retrieval task with graded distractors gives us a mechanical sub-oracle for "did the
    agent find the right prior work".
  - The ranking task (gold vs. negatives, both orders) is a mechanical way to test whether a
    model can *recognise* the target without having to generate it.
- **Does not fit:**
  - There is no data in the pack.
  - The hidden target is a prose hypothesis, and composition is judged by an LLM.
  - There are no numeric or symbolic targets.
  - Many disciplines and many review papers produce targets that no simulator or data fit
    could check.
  - The NC data license makes redistribution inside our repo awkward.

---

## 4. MOOSE-Chem (arXiv 2410.07076, ICLR 2025)

This is the rediscovery benchmark that ResearchBench grew out of. The LLM4SR survey was
**not read** (blocked), so these notes come from the MOOSE-Chem repo.

### 4.1 What one task contains
`Data/chem_research_2024.xlsx`, sheet `Overall`, has 51 rows (one per paper). Columns:
`No, Title, Public Date, Publisher, Background Little Survey, Background Little Survey (strict),
Background Question, Background Question (strict), Main Inspiration, Inspiration paper 1..3 title,
Relation between the main inspiration and the inspiration paper 1..3, Main hypothesis,
Experiments to Verify the Research Hypothesis:, Reasoning Process, Note`.
Other sheets (`Wanhao`, `Wanhao_checked`, ...) hold per-annotator versions. The paper says
PhD chemists annotated them *[search-snippet]*.

Separate files hold the inspiration corpora: `Inspiration_Corpus_{150,300,1000,3000}.json`,
each a list of `[title, abstract]`.

Real example (row 0):
- Title: "Ultrastrong, flexible thermogalvanic armor with a Carnot-relative efficiency over 8%".
  Public Date 2024/08/07, Nature Communications.
- Background Question: *"How can we design a flexible thermogalvanic device that simultaneously
  maximizes both Carnot-relative efficiency and mechanical robustness...?"*
- Inspirations: "Interactions between macromolecules and ions: the Hofmeister series"; "Beyond
  Hofmeister"; "Strong tough hydrogels via the synergy of freeze-casting and salting out".
- Main hypothesis: (Gdm)2SO4 in a PVA hydrogel plus directional freezing gives Carnot-relative
  efficiency >8% with high mechanical strength.
- Experiments: the measured 8.53% efficiency, 900% stretch, and so on.
- Reasoning Process: `bkg + insp1/insp2 + insp3 = hyp`.

### 4.2 Scoring
- **An LLM judge:** "Matched score", a 6-point Likert scale (5 to 0), based on how many key
  points of the ground-truth hypothesis are covered (`eval_matched_score` prompt in
  `Method/utils.py`).
- Plus a **mechanical** inspiration hit ratio during screening (`Analysis/analysis.py`).
- Plus expert human evaluation for selected hypotheses (`Expert_Evaluation/*.json`).

### 4.3 Contamination / cutoff
Target papers were published or online in 2024, and the models used have training data up to
October 2023 (README). This is a hard date split by construction. The "strict" columns appear to
be a background-survey variant with less of the answer leaked (column naming; I did not verify
the meaning in the paper).

### 4.4 License / location
- MIT (repo `LICENSE`). Data is in the repo under `Data/`.
- Abstracts in the corpora come from publishers (Web of Science export).

### 4.5 Reuse for our schema
- **Reusable:**
  - `Public Date` plus a model-cutoff split.
  - The background survey works as a *text knowledge pack*, and its strict/non-strict variants
    are a leak-control idea.
  - The inspirations with explicit "relation" text.
  - The `Reasoning Process` formula (`bkg + insp1 + insp2 = hyp`) is a nice compact
    "derivation path" field.
  - `Experiments to Verify` holds numeric results (8.53%) that *could* become a numeric
    target, though only if we had a predictive model of them, which we do not.
- **Does not fit:**
  - The target is a qualitative design hypothesis in chemistry, and the oracle is an LLM
    matched-score.
  - There is no data or simulator.
  - At 51 papers it is small, and the format is Excel rather than a structured file.

---

## 5. LLMLagBench (arXiv 2511.12116)

This is a probe of knowledge cutoffs, not a discovery benchmark. **The arXiv PDF, the HF Space
(`pelcra-llmlagbench.hf.space`) and every mirror failed to load.** I found no GitHub repo
(searches for `LLMLagBench` and `org:pelcra` returned nothing) and no HF dataset. Everything
below is *[search-snippet]*.

### 5.1 What one task contains
- About 1,700 questions (1,713 cited) drawn from news reports published January 2021 to
  October 2025, one dated event per question. They were selected manually; an LLM-based
  extractor helped generate candidates, and the authors note it sometimes produced trivial
  questions.
- **Exact fields and an example instance: not verified.** The items presumably include a
  question, a reference answer and an event date, but I could not confirm this.

### 5.2 Scoring
- Each answer gets a faithfulness score on a 0-2 scale from an evaluator LLM, which makes this
  **an LLM judge**. The judge model's name was not found.
- Refusals are tracked separately.
- The cutoff is estimated mechanically with **PELT changepoint detection** on the time-ordered
  score series. It can find several partial cutoffs, unlike CutoffBench's single transition.

### 5.3 Contamination / cutoff
Measuring the cutoff is the benchmark's whole purpose. Reported finding: cutoffs declared by
providers and models' own claims often differ from the measured boundaries by months or years.

### 5.4 License / location
- Paper listed as CC BY 4.0 on ResearchGate *[search-snippet, not authoritative]*.
- There is a leaderboard on the HF Space. **No dataset release found.**

### 5.5 Reuse for our schema
- **Reusable:**
  - The *method*, not the format: measure each model's actual cutoff empirically instead of
    trusting the declared date. We could do this with LLMLagBench's leaderboard numbers or
    our own probe. A task's "contamination" label (e.g. `total` for Kepler) could then be set
    relative to the measured boundary.
  - The partial-cutoff finding argues for storing a cutoff *range* per model, not a single date.
- **Does not fit:** it is not a discovery task: it has no pack, no oracle and no hidden law.

---

## Recommendations for /tasks format

Our current `tasks/kepler_third_law/task.yaml` already has most of the right shape: a pack `.md`
file, `data/`, `hidden/`, an oracle block with `llm_free: true`, variants and a contamination
note. None of the five benchmarks has a mechanical oracle for the main discovery target. All of
them fall back to an LLM judge (FIRE-Bench, DBench-Bio, ResearchBench composition, MOOSE-Chem)
or to human experts. **The oracle is what sets our format apart, so keep `llm_free: true`
required for the primary score.** Changes I would make:

1. **Split visible and hidden files explicitly, as FIRE-Bench does.** Keep `pack_*.md` and
   `data/` for the agent, and keep `hidden/` for the target, holdout and a new optional
   `hidden/derivation.md`. Like FIRE-Bench's `instruction_gt.txt`, this file records how the
   result was actually reached; it is never scored but helps diagnose failures.
2. **Add a structured `literature` list to the pack**, following the
   ResearchBench/MOOSE-Chem `inspirations[{title, year, abstract_or_summary, relation}]`. Each
   entry should carry a date that must be at or before the pack's `as_of` date. A schema test
   can then check mechanically that no pack item is dated after the cutoff.
3. **Add dates and provenance fields:**
   - `as_of` (pack snapshot date, e.g. 1618-05)
   - `target_published` (the date the result was published)
   - `source` (DOI or citation)
   - `status: verified | unverified`, as in FIRE-Bench
4. **Treat contamination per model, not per task.** Keep the `Contamination: total` note, and
   also allow comparing `target_published` with each model's *measured* cutoff range, as
   LLMLagBench argues. For historical tasks this is always "total", which is why the
   synthetic-variant pattern (as in Kepler) should stay mandatory for any task we report as
   measuring discovery rather than recall.
5. **Add `resources`/`constraints` blocks**, as in FIRE-Bench's `task_config.yaml`: tool
   budget, no-web-search, and allowed libraries. These are enforced by the harness, not only
   stated in the prompt (FIRE-Bench relied on the prompt and checked afterwards).
6. **Optional auxiliary mechanical scores.** These are borrowed from ResearchBench:
   - an inspiration-retrieval hit ratio over a candidate pool with graded hard negatives;
   - a pairwise "gold versus distractor law" recognition check (both orders).
   Both are LLM-free and cheap, and they separate "can recognise" from "can derive".
7. **Do not import their task data directly.**
   - FIRE-Bench (no license; LLM-behaviour domain) and DBench-Bio (no data released; no
     license) have nothing to import.
   - ResearchBench is CC BY-NC, and its targets are prose.
   - MOOSE-Chem (MIT) is the only one licensed cleanly enough to adapt. Its targets would
     still need a new oracle, which is not possible for qualitative chemistry design
     hypotheses.
   - FIRE-Bench verified tasks with bundled data and directional findings (e.g.
     lost-in-the-middle) are the most promising to rewrite with a mechanical data-check
     oracle, after asking the authors about the license.

## Sources

- FIRE-Bench repo: https://github.com/maitrix-org/FIRE-Bench. Paper PDF via
  https://github.com/firebench/firebench.github.io (`static/FIRE_Bench.pdf`). arXiv
  https://arxiv.org/abs/2602.02905 (not loaded).
- DBench-Bio repo: https://github.com/transcend-0/DBench-Bio. arXiv
  https://arxiv.org/abs/2603.03322 and https://pith.science/paper/2603.03322 (not loaded).
- ResearchBench repo: https://github.com/ankitala/ResearchBench. HF
  https://huggingface.co/datasets/ankilok/ResearchBench (not loaded). arXiv
  https://arxiv.org/pdf/2503.21248 (not loaded).
- MOOSE-Chem repo: https://github.com/ZonglinY/MOOSE-Chem. arXiv
  https://arxiv.org/abs/2410.07076 (not loaded). LLM4SR https://arxiv.org/html/2501.04306v1
  (not loaded).
- LLMLagBench: https://arxiv.org/pdf/2511.12116v1 and https://pelcra-llmlagbench.hf.space/
  (neither loaded; search snippets only).
