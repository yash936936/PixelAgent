"""
Adversarial/evasive-phrasing eval harness for the safety layer
(risk_classifier.py + boundary_guard.py, and any future RiskModelBackend --
see src/brain/risk_model_backend.py). This is the harness whose existence
was promised in the last review pass: build it BEFORE deployment, not
after.

Usage:
    python -m eval.adversarial_boundary_eval                # baseline: keyword-only
    python -m eval.adversarial_boundary_eval --model local   # also score a RiskModelBackend

See eval/README.md for what the pass/fail thresholds mean and why "local"
mode requires a running local model endpoint.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.brain import boundary_guard
from src.brain.risk_classifier import Risk, RiskClassifier

_CASES_PATH = Path(__file__).parent / "adversarial_cases.jsonl"


@dataclass
class CaseResult:
    case_id: str
    category: str
    expected: str
    predicted: str
    correct: bool
    note: str = ""


def _load_cases() -> list[dict]:
    cases = []
    with open(_CASES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _predict_keyword_only(step: dict) -> str:
    """Baseline prediction using exactly what orchestrator.py runs today:
    boundary_guard first (non-negotiable), then the keyword-based
    RiskClassifier."""
    violation = boundary_guard.check(step)
    if violation is not None:
        return f"boundary:{violation.boundary.value}"
    return RiskClassifier().classify(step).value


def _predict_with_model(step: dict, judge: Callable[[dict], Risk | None]) -> str:
    """Same as _predict_keyword_only, but layers a RiskModelBackend's
    opinion on top exactly the way orchestrator.py's _classify_risk() does:
    boundary_guard first (a trained model never overrides this), keyword
    match if confident, model opinion only consulted for the unmatched
    case, and only ever escalating Local -> External/Destructive."""
    violation = boundary_guard.check(step)
    if violation is not None:
        return f"boundary:{violation.boundary.value}"

    risk, confident = RiskClassifier().classify_with_confidence(step)
    if confident:
        return risk.value

    model_opinion = judge(step)
    if model_opinion is not None and model_opinion != Risk.LOCAL:
        return model_opinion.value
    return risk.value


def run(judge: Callable[[dict], Risk | None] | None = None) -> list[CaseResult]:
    results = []
    for case in _load_cases():
        if judge is None:
            predicted = _predict_keyword_only(case["step"])
        else:
            predicted = _predict_with_model(case["step"], judge)

        results.append(
            CaseResult(
                case_id=case["id"],
                category=case["category"],
                expected=case["expected_risk"],
                predicted=predicted,
                correct=predicted == case["expected_risk"],
                note=case.get("note", ""),
            )
        )
    return results


def summarize(results: list[CaseResult]) -> dict:
    """Reports overall accuracy plus, critically, per-category recall --
    a model that's 90% accurate overall but 40% recall on
    evasive_destructive cases is NOT safe to deploy, and averaging would
    hide exactly that. See eval/README.md for the threshold this feeds."""
    by_category: dict[str, list[CaseResult]] = {}
    for r in results:
        by_category.setdefault(r.category, []).append(r)

    summary = {
        "total": len(results),
        "correct": sum(1 for r in results if r.correct),
        "accuracy": sum(1 for r in results if r.correct) / len(results) if results else 0.0,
        "by_category": {},
    }
    for category, cat_results in by_category.items():
        correct = sum(1 for r in cat_results if r.correct)
        summary["by_category"][category] = {
            "total": len(cat_results),
            "correct": correct,
            "recall": correct / len(cat_results) if cat_results else 0.0,
        }
    return summary


def print_report(results: list[CaseResult]) -> dict:
    summary = summarize(results)
    print(f"Overall: {summary['correct']}/{summary['total']} ({summary['accuracy']:.0%})\n")
    print("By category (this is what actually matters — see eval/README.md):")
    for category, stats in sorted(summary["by_category"].items()):
        marker = "OK " if stats["recall"] == 1.0 else "!! "
        print(f"  {marker}{category}: {stats['correct']}/{stats['total']} ({stats['recall']:.0%})")

    failures = [r for r in results if not r.correct]
    if failures:
        print(f"\n{len(failures)} failing case(s):")
        for r in failures:
            print(f"  [{r.case_id}] expected={r.expected!r} predicted={r.predicted!r}  {r.note}")

    return summary


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", choices=["none", "local", "hosted"], default="none",
        help="Also score a RiskModelBackend on top of the keyword baseline. "
             "'local'/'hosted' require the matching config.py endpoint to be reachable.",
    )
    args = parser.parse_args()

    judge = None
    if args.model != "none":
        from src import config
        from src.brain.planner import HostedLLMPlanner, build_http_generate_fn
        from src.brain.risk_model_backend import HostedRiskJudge, LocalFineTunedRiskModel

        cfg = config.load()
        if args.model == "local":
            if not cfg.local_risk_model_endpoint:
                raise RuntimeError("LOCAL_RISK_MODEL_ENDPOINT must be set to eval a local model.")
            judge = LocalFineTunedRiskModel(
                generate_fn=build_http_generate_fn(cfg.local_risk_model_endpoint)
            ).judge
        else:
            generate_fn = HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)._generate_fn
            judge = HostedRiskJudge(generate_fn=generate_fn).judge

    results = run(judge)
    print_report(results)


if __name__ == "__main__":
    _main()
