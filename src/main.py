"""
Thin harness entry point — wires subsystems together, no business logic of
its own (per docs/CODE_LOGIC.md §8). Run as:
    python -m src.main "your instruction here"
"""
from __future__ import annotations

import sys

from src import config
from src.action.action_router import ActionRouter
from src.action.playwright_driver import PlaywrightDriver
from src.brain.orchestrator import Orchestrator
from src.brain.planner import HostedLLMPlanner
from src.confirmation.gate import ConfirmationGate
from src.confirmation.prompt_ui import console_prompt
from src.observability.logger import Logger


def main(instruction: str) -> dict:
    cfg = config.load()

    logger = Logger(cfg.log_dir)
    planner = HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)
    gate = ConfirmationGate(prompt_fn=console_prompt)

    with PlaywrightDriver(cfg.default_chrome_profile, cfg.profiles_dir) as driver:
        router = ActionRouter(playwright_driver=driver)
        orchestrator = Orchestrator(
            planner=planner,
            driver=driver,
            action_router=router,
            gate=gate,
            logger=logger,
            max_steps=cfg.max_steps_per_task,
        )
        result = orchestrator.run_task(instruction)

    print(f"\nTask finished with status: {result['status']}")
    print(f"Full trace: {logger.log_path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python -m src.main "your instruction here"')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))
