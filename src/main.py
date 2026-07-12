"""
Thin harness entry point — wires subsystems together, no business logic of
its own (per docs/CODE_LOGIC.md §8). Run as:
    python -m src.main "your instruction here"
"""
from __future__ import annotations

import sys

from src import config
from src.action.action_router import ActionRouter
from src.action.mouse_keyboard import MouseKeyboard
from src.action.playwright_driver import PlaywrightDriver
from src.brain.orchestrator import Orchestrator
from src.brain.planner import HostedLLMPlanner, LocalFineTunedPlanner, build_http_generate_fn
from src.brain.replanner import Replanner
from src.brain.risk_model_backend import HostedRiskJudge, LocalFineTunedRiskModel
from src.confirmation.gate import ConfirmationGate
from src.confirmation.prompt_ui import console_prompt
from src.memory.memory_api import MemoryAPI
from src.observability.logger import Logger
from src.perception.ocr import OCREngine


def _build_risk_model_judge(cfg):
    """Track B (docs/DECISIONS.md 2026-07-12): builds the SEPARATE
    risk/boundary judgment model, independent of _build_planner() below --
    deliberately not reusing the planner's transport, so the two models can
    be swapped/rolled back independently (see risk_model_backend.py's
    docstring and config.py's risk_model_backend/local_risk_model_endpoint
    fields).

    Defaults to returning None (risk_model_backend="none") -- i.e.
    risk_classifier.py's keyword floor + boundary_guard.py remain the ONLY
    risk signal unless a trained/hosted risk model is explicitly enabled.
    This default is deliberate: enabling "local" here is a deployment
    decision that requires the eval/adversarial_boundary_eval.py gate to
    have been run and passed first (see eval/README.md) -- main.py cannot
    verify that gate was actually run, so it does not try to; it only
    keeps the safer default until a human opts in."""
    if cfg.risk_model_backend == "none":
        return None

    if cfg.risk_model_backend == "hosted":
        generate_fn = HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)._generate_fn
        return HostedRiskJudge(generate_fn=generate_fn).judge

    if cfg.risk_model_backend == "local":
        if not cfg.local_risk_model_endpoint:
            raise RuntimeError(
                "RISK_MODEL_BACKEND=local requires LOCAL_RISK_MODEL_ENDPOINT to be set in .env. "
                "Before enabling this, run eval/adversarial_boundary_eval.py against the model "
                "and confirm it clears the recall threshold in eval/README.md."
            )
        generate_fn = build_http_generate_fn(cfg.local_risk_model_endpoint)
        return LocalFineTunedRiskModel(generate_fn=generate_fn).judge

    return None


def _build_desktop_backends():
    """Desktop control (MouseKeyboard) and OCR require a real display/OS and
    the Tesseract binary respectively — both optional at runtime. If either
    is unavailable, Pixel still works for browser-only tasks; only
    target_type='desktop' steps require them (see docs/PHASES.md Part 2.2)."""
    try:
        mouse_keyboard = MouseKeyboard()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Desktop control unavailable ({exc}); web-only mode.")
        mouse_keyboard = None

    ocr_engine = OCREngine()  # cheap to construct; fails only when .read() is called
    return mouse_keyboard, ocr_engine


def _build_planner(cfg):
    """Track B (docs/DECISIONS.md 2026-07-12): PLANNER_BACKEND=local swaps
    in a LoRA-fine-tuned local model for routine steps instead of the
    hosted Gemini API, behind the same PlannerBackend interface -- risk
    classification and confirmation gating in orchestrator.py are
    unaffected either way. See docs/TRD.md §6 and training/README.md."""
    if cfg.planner_backend == "local":
        if not cfg.local_planner_endpoint:
            raise RuntimeError(
                "PLANNER_BACKEND=local requires LOCAL_PLANNER_ENDPOINT to be set in .env."
            )
        generate_fn = build_http_generate_fn(cfg.local_planner_endpoint)
        return LocalFineTunedPlanner(generate_fn=generate_fn)
    return HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)


def main(instruction: str) -> dict:
    cfg = config.load()

    logger = Logger(cfg.log_dir)
    planner = _build_planner(cfg)
    gate = ConfirmationGate(prompt_fn=console_prompt)
    replanner = Replanner(planner=planner)
    memory = MemoryAPI(log_dir=cfg.log_dir)
    mouse_keyboard, ocr_engine = _build_desktop_backends()

    with PlaywrightDriver(cfg.default_chrome_profile, cfg.profiles_dir) as driver:
        router = ActionRouter(
            playwright_driver=driver, mouse_keyboard=mouse_keyboard, ocr_engine=ocr_engine
        )
        orchestrator = Orchestrator(
            planner=planner,
            driver=driver,
            action_router=router,
            gate=gate,
            logger=logger,
            max_steps=cfg.max_steps_per_task,
            mouse_keyboard=mouse_keyboard,
            replanner=replanner,
            memory=memory,
            log_dir=cfg.log_dir,
            llm_risk_judge=_build_risk_model_judge(cfg),
        )
        result = orchestrator.run_task(instruction)

    memory.close()
    print(f"\nTask finished with status: {result['status']}")
    print(f"Full trace: {logger.log_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python -m src.main "your instruction here"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
