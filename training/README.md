# Training — Track B (two separate models, per docs/DECISIONS.md 2026-07-12)

This directory scaffolds two **independent** training runs. They are kept
separate deliberately (separate data, separate scripts, separate model
artifacts, separate config entries in `src/config.py`) because they have
different trust levels — see `src/brain/risk_model_backend.py`'s module
docstring for the full rationale. Do not merge them into a single
multi-task fine-tune; a single model tuned on both objectives makes it
harder to evaluate, version, and roll back the safety-critical one
independently of the lower-stakes one.

**Nothing in this directory can actually be run in the sandbox this project
was built in** — there is no GPU, no persistent storage across sessions,
and (most importantly) no real training data yet, since `docs/STATUS.md`
is explicit that zero live task runs have ever happened. Everything here
is a correct, ready-to-run scaffold for you to execute on real hardware
once real usage data exists. Treat the scripts as a starting point to
adapt, not a black box to trust blindly.

## The two runs

### 1. Planner model → `LocalFineTunedPlanner` (`src/brain/planner.py`)
- **Objective:** given `(instruction, screen_state, history)`, predict the
  same single-next-step JSON `HostedLLMPlanner` produces.
- **Data source:** successful episodic-memory traces (`memory/episodic_store.py`,
  status `"done"`) once real tasks have run — each step in a successful
  episode is one training example.
- **Stakes if wrong:** low-to-medium. A bad planner step still passes
  through `risk_classifier.py` + `boundary_guard.py` + the confirmation
  gate untouched — see `training/prepare_dataset.py --target planner`.

### 2. Risk model → `LocalFineTunedRiskModel` (`src/brain/risk_model_backend.py`)
- **Objective:** given a proposed step, predict `local`/`external`/`destructive`
  — an ADDITIVE signal on top of the keyword floor, never a replacement.
- **Data source:** `eval/adversarial_cases.jsonl` (the adversarial set) PLUS
  real corrections mined from trace logs via
  `src/observability/trace_replay.py`'s `unclassified_or_missing_risk()`
  once live logs exist — see `training/prepare_dataset.py --target risk_model`.
- **Stakes if wrong:** high — see `eval/README.md`'s deployment-gate
  thresholds, which this model MUST clear before `RISK_MODEL_BACKEND=local`
  is ever set in a live `.env`.

## Recommended base model

A small open-weights instruct model that fits comfortably on a single
consumer GPU (12-24GB VRAM) for LoRA fine-tuning:
- **Qwen2.5-3B-Instruct** or **Qwen2.5-7B-Instruct** — strong instruction-
  following and JSON-mode reliability at small size, Apache 2.0 license.
- **Llama-3.2-3B-Instruct** — comparable alternative, Meta's community license.

Either works for both training runs; you do not need the same base model for
both, and keeping them different is a reasonable extra layer of
independence (e.g. planner on Qwen2.5-7B for richer step reasoning, risk
model on the smaller/cheaper 3B since its output space is only 3 classes).

**Whichever you choose, it must ship with intact safety training and be
used as-is (LoRA only, no full-parameter safety-relevant re-tuning, no
merging with a "de-safetied" community checkpoint)** — this is `TRD.md §6`'s
hard requirement, and `training/model_card_template.md` below is where you
record which exact checkpoint you used so this is auditable later, not
just asserted.

## Pipeline

```
1. prepare_dataset.py   -- turns raw sources into instruction-tuned jsonl
2. train_lora.py         -- runs the actual LoRA fine-tune (needs a GPU machine)
3. eval/adversarial_boundary_eval.py --model local   -- the deployment gate
4. model_card_template.md -- fill out and commit before flipping RISK_MODEL_BACKEND=local
5. docs/DECISIONS.md + docs/TRD.md §6 -- record the decision (see template below)
```

## docs/DECISIONS.md entry template for when you actually train a model

```
### [DATE] Track B model deployment: <planner|risk_model>
- Base model: <exact HF repo + commit/revision>
- Training data: <source, size, date range>
- Fine-tuning method: LoRA, rank=<r>, alpha=<a>, target_modules=<...>
- Eval results (risk_model only): link to eval/adversarial_boundary_eval.py
  output, per-category recall table, confirmation it clears eval/README.md's
  thresholds
- Safety review: confirm base model has intact safety training, no
  de-safetied checkpoint used (TRD.md §6)
- Rollback plan: how to revert to keyword-only / hosted backend if this
  underperforms in production
```
