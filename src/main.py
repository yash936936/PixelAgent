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
from src.brain.planner import HostedLLMPlanner, LocalPlanner, build_http_generate_fn
from src.brain.replanner import Replanner
from src.brain.risk_llm_judge import build_llm_risk_judge
from src.confirmation.gate import ConfirmationGate
from src.confirmation.prompt_ui import console_prompt
from src.memory.memory_api import MemoryAPI
from src.observability.logger import Logger
from src.perception.ocr import OCREngine


def _build_llm_risk_judge(planner):
    """Fix for a gap flagged in review: this fallback previously didn't
    exist at all despite risk_classifier.py's docstring long promising it.
    Reuses whichever planner backend is already configured (hosted Gemini
    or a local endpoint) so no second LLM client/config is needed --
    HostedLLMPlanner and LocalPlanner both already expose a
    generate/next_step path; here we just need a raw (system, user) ->
    text callable, so we go one level lower than next_step() and reuse the
    same transport LocalPlanner already wraps for hosted vs local. If the
    planner doesn't expose that transport, risk judging simply falls back
    to keyword-only classification (identical to every prior phase's
    behavior) rather than failing startup."""
    generate_fn = getattr(planner, "_generate_fn", None)
    if generate_fn is None:
        return None
    return build_llm_risk_judge(generate_fn)


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
    """Phase 4 (optional): PLANNER_BACKEND=local swaps in a cheaper
    locally-hosted model for routine steps instead of the hosted Gemini
    API, behind the same PlannerBackend interface -- risk classification
    and confirmation gating in orchestrator.py are unaffected either way.
    See docs/TRD.md §6 and docs/PHASES.md Phase 4."""
    if cfg.planner_backend == "local":
        if not cfg.local_planner_endpoint:
            raise RuntimeError(
                "PLANNER_BACKEND=local requires LOCAL_PLANNER_ENDPOINT to be set in .env."
            )
        generate_fn = build_http_generate_fn(cfg.local_planner_endpoint)
        return LocalPlanner(generate_fn=generate_fn)
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
            llm_risk_judge=_build_llm_risk_judge(planner),
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
