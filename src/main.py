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
from src.brain.risk_model_backend import HostedRiskJudge, LocalFineTunedRiskModel, SemanticRiskJudge
from src.confirmation.gate import ConfirmationGate
from src.confirmation.prompt_ui import console_prompt
from src.memory.memory_api import MemoryAPI
from src.observability.logger import Logger, prune_old_logs
from src.observability.operational_limits import OperationalLimits, TaskConcurrencyGuard
from src.perception.ocr import OCREngine

# Phase 15 (2026-08-11, docs/DECISIONS.md): a SINGLE, process-wide
# TaskConcurrencyGuard, constructed once at module import time rather than
# per-task-run inside main(). This matters: if a new guard were constructed
# on every main() call, the concurrency ceiling would never actually be
# shared across calls and would be meaningless (every task would see an
# empty guard and always succeed). Since `python -m src.main "..."` and the
# `pixel` console command both invoke main()/cli_main() as a fresh process
# per invocation, this guard is only genuinely process-wide within a single
# process's lifetime -- e.g. if src.main is ever imported and main() called
# multiple times within one long-running process (not how the CLI is used
# today, but how a future test harness or the Phase 13
# container-orchestration HTTP API might call it). For the ordinary
# one-process-per-CLI-invocation case, this guard's practical effect today
# is limited to catching a genuine re-entrant call within that one process
# -- it is NOT a cross-process lock (two separate `pixel "..."` invocations
# in two separate terminals are two separate processes with two separate
# guards, so this does not yet prevent that case; see
# src/observability/operational_limits.py's TaskConcurrencyGuard docstring
# for why cross-process locking was explicitly out of scope for this pass).
_CONCURRENCY_GUARD = TaskConcurrencyGuard(max_concurrent=None)  # sized from real cfg in main() below


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

    if cfg.risk_model_backend == "semantic":
        # Zero-dependency, in-process, no network/GPU/endpoint required --
        # unlike "hosted"/"local" this needs no eval/README.md deployment
        # gate before enabling (see SemanticRiskJudge's own docstring for
        # why: it fails open to "no opinion" exactly like every other
        # backend here, and it's a same-day improvement over the keyword
        # floor, not a trained model making opaque decisions).
        return SemanticRiskJudge().judge

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


def _build_desktop_backends(cfg):
    """Desktop control (MouseKeyboard) and OCR require a real display/OS and
    the Tesseract binary respectively — both optional at runtime. If either
    is unavailable, Pixel still works for browser-only tasks; only
    target_type='desktop' steps require them (see docs/PHASES.md Part 2.2).

    cfg.tesseract_cmd (2026-08-01, Phase 7 prep) lets OCREngine find
    Tesseract when it's installed but not on PATH -- the exact failure mode
    src/doctor.py's Tesseract check surfaces. None (the default) falls back
    to relying on PATH, unchanged from before.

    cfg.execution_mode == "browser_only" (2026-08-02, Phase 12,
    docs/DECISIONS.md): skips even attempting to construct MouseKeyboard.
    This is a distinct, better startup experience than the generic
    "unavailable" warning below -- inside the Docker image (Dockerfile),
    desktop control isn't accidentally missing, it's structurally
    impossible (no real display exists in a headless Linux container), so
    the message should say that plainly rather than looking like a
    runtime failure worth investigating."""
    if cfg.execution_mode == "browser_only":
        print(
            "[info] EXECUTION_MODE=browser_only — desktop control is intentionally disabled "
            "(e.g. running in the Docker image, which has no real display). Browser-only "
            "tasks are unaffected; any target_type='desktop' step will fail immediately and "
            "explicitly rather than mid-task."
        )
        mouse_keyboard = None
    else:
        try:
            mouse_keyboard = MouseKeyboard()
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] Desktop control unavailable ({exc}); web-only mode.")
            mouse_keyboard = None

    ocr_engine = OCREngine(tesseract_cmd=cfg.tesseract_cmd)  # cheap to construct; fails only when .read() is called
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
    return HostedLLMPlanner(
        api_key=cfg.gemini_api_key,
        model=cfg.llm_model,
        rate_limit_max_attempts=cfg.rate_limit_max_attempts,
        rate_limit_max_backoff_seconds=cfg.rate_limit_max_backoff_seconds,
    )


def _build_operational_limits(cfg) -> OperationalLimits:
    """Phase 15 (2026-08-11, docs/DECISIONS.md): translates cfg's three
    MAX_COST_USD/MAX_WALL_CLOCK_SECONDS/MAX_CONCURRENT_TASKS fields into the
    OperationalLimits bundle Orchestrator expects. Kept as its own small
    function (matching _build_planner/_build_risk_model_judge/
    _build_desktop_backends's existing pattern) rather than inlined, so
    src/gui/worker.py can import and reuse it identically instead of
    re-deriving the same three fields separately -- avoids the exact
    CLI/GUI-parity miss this project has hit twice before (TESSERACT_CMD,
    AUTO_APPROVE_EXTERNAL) by construction this time, not as a later
    follow-up fix."""
    return OperationalLimits(
        max_cost_usd=cfg.max_cost_usd,
        max_wall_clock_seconds=cfg.max_wall_clock_seconds,
        max_concurrent_tasks=cfg.max_concurrent_tasks,
    )


def main(instruction: str) -> dict:
    cfg = config.load()

    # Phase 15: size the module-level concurrency guard from real config on
    # first real use. _CONCURRENCY_GUARD.acquire()/.release() still work
    # correctly even if this races across threads (TaskConcurrencyGuard's
    # own lock protects _active_count), but max_concurrent itself is set
    # once here rather than at import time, since cfg isn't available yet
    # at module import.
    _CONCURRENCY_GUARD._max_concurrent = cfg.max_concurrent_tasks  # noqa: SLF001 - see note above

    # Phase 8 (2026-08-02, docs/DECISIONS.md): day-based retention for
    # trace logs/screenshots, run once at startup before this task's own
    # log file is created (so the brand-new file is never a pruning
    # candidate).
    deleted = prune_old_logs(cfg.log_dir, cfg.log_retention_days)
    if deleted:
        print(f"[info] Pruned {deleted} log/screenshot file(s) older than {cfg.log_retention_days} day(s).")

    logger = Logger(cfg.log_dir)
    planner = _build_planner(cfg)
    if cfg.auto_approve_external:
        print(
            "[warn] AUTO_APPROVE_EXTERNAL=true — External-risk steps will be approved with NO "
            "confirmation prompt shown. Destructive-risk steps are UNAFFECTED and will always still "
            "require the interactive confirm phrase. See docs/DECISIONS.md 2026-08-01 for why this "
            "exists and its exact boundaries."
        )
    gate = ConfirmationGate(prompt_fn=console_prompt, auto_approve_external=cfg.auto_approve_external)
    replanner = Replanner(planner=planner)
    memory = MemoryAPI(log_dir=cfg.log_dir)
    mouse_keyboard, ocr_engine = _build_desktop_backends(cfg)

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
            operational_limits=_build_operational_limits(cfg),
            concurrency_guard=_CONCURRENCY_GUARD,
        )
        try:
            result = orchestrator.run_task(instruction)
        except Exception as exc:
            # Phase 15: OperationalLimitExceeded raised from
            # acquire_task_limits_session() itself (i.e. the concurrency
            # ceiling was already at capacity before this task even started)
            # propagates here rather than being caught inside run_task() --
            # see orchestrator.py's run_task() docstring/comment for why.
            # Surfaced as a clear, actionable message rather than a raw
            # traceback, matching this project's existing convention for
            # startup-time failures (e.g. ChromeProfileLaunchError's message).
            from src.observability.operational_limits import OperationalLimitExceeded

            if isinstance(exc, OperationalLimitExceeded):
                print(f"[error] {exc}")
                raise
            raise

    memory.close()
    print(f"\nTask finished with status: {result['status']}")
    print(f"Full trace: {logger.log_path}")
    return result


def cli_main() -> None:
    """Zero-argument entry point for the `pixel` console command
    (pyproject.toml's [project.scripts], Phase 11, docs/DECISIONS.md
    2026-08-02) -- reads sys.argv itself, since console_scripts entry
    points are called with no arguments. `python -m src.main "..."` below
    still works identically; this is the same logic, just callable from an
    installed command on PATH instead of only from inside a source
    checkout."""
    if len(sys.argv) < 2:
        print('Usage: pixel "your instruction here"  (or: python -m src.main "your instruction here")')
        sys.exit(1)
    main(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    cli_main()
