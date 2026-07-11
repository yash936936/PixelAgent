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
from src.brain.planner import HostedLLMPlanner
from src.brain.replanner import Replanner
from src.confirmation.gate import ConfirmationGate
from src.confirmation.prompt_ui import console_prompt
from src.memory.memory_api import MemoryAPI
from src.observability.logger import Logger
from src.perception.ocr import OCREngine


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


def main(instruction: str) -> dict:
    cfg = config.load()

    logger = Logger(cfg.log_dir)
    planner = HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)
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
