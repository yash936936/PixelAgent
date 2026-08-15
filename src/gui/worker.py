"""
Runs Orchestrator.run_task() on a background QThread so the GUI never
blocks, and bridges the confirmation gate (which orchestrator.py calls
synchronously, expecting an immediate return) across to the GUI thread where
the actual dialog has to be shown. Uses a Qt::BlockingQueuedConnection: the
worker thread's call blocks until the GUI-thread slot finishes, which is
exactly the semantic ConfirmationGate.request_approval() needs — see
docs/CODE_LOGIC.md §6 for the underlying observe/plan/act loop this wraps.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal

from src.action.action_router import ActionRouter
from src.action.mouse_keyboard import MouseKeyboard
from src.action.playwright_driver import PlaywrightDriver
from src.brain.orchestrator import Orchestrator
from src.brain.replanner import Replanner
from src.confirmation.gate import ConfirmationGate, GateContext
from src.gui.widgets.confirmation_dialog import ConfirmationDialog
from src.memory.memory_api import MemoryAPI
from src.observability.logger import Logger
from src.observability.operational_limits import TaskConcurrencyGuard
from src.perception.ocr import OCREngine

# Phase 15 (2026-08-11, docs/DECISIONS.md): a SEPARATE process-wide guard
# from src/main.py's _CONCURRENCY_GUARD -- the CLI and GUI are two distinct
# entry points/processes (per this project's long-standing CLI/GUI-parity
# convention, they don't share Python module state across a process
# boundary), so each needs its own module-level guard, sized from real
# config the same way main.py's is. If the GUI and CLI both ran in the SAME
# process someday (not how either is invoked today), this would need
# consolidating into one shared guard -- flagged here rather than silently
# assumed correct forever.
_CONCURRENCY_GUARD = TaskConcurrencyGuard(max_concurrent=None)


class GateBridge(QObject):
    """Lives on the GUI thread. The worker thread calls .ask(...), which
    emits a BlockingQueuedConnection signal — execution on the worker thread
    genuinely pauses at .emit() until MainWindow's connected slot returns,
    which is when the user has closed the ConfirmationDialog."""

    request_confirmation = Signal(dict, str, object)

    def __init__(self) -> None:
        super().__init__()
        self._pending_decision = None

    def ask(self, step: dict, risk, context: GateContext | None):
        self.request_confirmation.emit(step, risk.value, context)
        return self._pending_decision

    def set_pending_decision(self, decision) -> None:
        self._pending_decision = decision

    def prompt_fn(self, step: dict, risk, context: GateContext | None = None):
        return self.ask(step, risk, context)


class TaskWorker(QThread):
    """One instance per task run. step_logged/gate_logged/task_finished are
    forwarding signals off a GuiLogger so the trace/stats panels update
    live; task_failed carries unexpected errors (e.g. Playwright/profile
    launch failure) that happen before the orchestrator's own error
    handling would catch them. Phase 15 (2026-08-11): also carries
    OperationalLimitExceeded raised before a task even starts (concurrency
    ceiling already at capacity) -- surfaced through the same task_failed
    signal as any other pre-task startup failure, so the GUI doesn't need a
    new signal type for this specific case."""

    step_logged = Signal(dict)
    gate_logged = Signal(dict)
    task_finished = Signal(dict)
    task_failed = Signal(str)

    def __init__(self, instruction: str, cfg, gate_bridge: GateBridge, parent=None) -> None:
        super().__init__(parent)
        self._instruction = instruction
        self._cfg = cfg
        self._gate_bridge = gate_bridge

    def run(self) -> None:
        from src.gui.gui_logger import GuiLogger  # local import: keeps logger.py Qt-free
        from src.observability.logger import prune_old_logs
        from src.observability.operational_limits import OperationalLimits

        try:
            # Phase 15: size the module-level concurrency guard from real
            # config, same pattern as main.py -- done here rather than at
            # import time, since self._cfg isn't available until this
            # TaskWorker is constructed.
            _CONCURRENCY_GUARD._max_concurrent = self._cfg.max_concurrent_tasks  # noqa: SLF001

            # Phase 8 (2026-08-02, docs/DECISIONS.md): same day-based
            # retention pruning as main.py's CLI path -- run once here too
            # rather than assuming main.py's own pruning already covered
            # it, since a GUI-only user may never invoke the CLI at all.
            prune_old_logs(self._cfg.log_dir, self._cfg.log_retention_days)

            logger = GuiLogger(
                self._cfg.log_dir,
                on_step=lambda rec: self.step_logged.emit(rec),
                on_gate=lambda rec: self.gate_logged.emit(rec),
            )

            from src.brain.planner import HostedLLMPlanner

            planner = HostedLLMPlanner(
                api_key=self._cfg.gemini_api_key,
                model=self._cfg.llm_model,
                rate_limit_max_attempts=self._cfg.rate_limit_max_attempts,
                rate_limit_max_backoff_seconds=self._cfg.rate_limit_max_backoff_seconds,
            )
            # Fix (2026-08-01, docs/DECISIONS.md): auto_approve_external was wired into main.py's
            # ConfirmationGate but never ported to this GUI worker path -- found while checking whether
            # a related lazy-launch fix also needed porting here. Defaults to False via cfg, so this is
            # a no-op unless the user has actually opted in.
            gate = ConfirmationGate(
                prompt_fn=self._gate_bridge.prompt_fn, auto_approve_external=self._cfg.auto_approve_external
            )
            replanner = Replanner(planner=planner)
            memory = MemoryAPI(log_dir=self._cfg.log_dir)

            # Fix (2026-08-02, docs/DECISIONS.md, Phase 12): execution_mode wired into main.py's
            # desktop-backend construction but ported here in the same pass this time, per the
            # earlier CLI/GUI-parity lesson (TESSERACT_CMD/AUTO_APPROVE_EXTERNAL were fixed in
            # main.py first and only found missing here later).
            if self._cfg.execution_mode == "browser_only":
                mouse_keyboard = None
            else:
                try:
                    mouse_keyboard = MouseKeyboard()
                except Exception:  # noqa: BLE001 — desktop control optional, see main.py
                    mouse_keyboard = None
            # Fix (2026-08-01, docs/DECISIONS.md): TESSERACT_CMD was wired into main.py's OCREngine
            # construction but never ported to this GUI worker path -- same gap as auto_approve_external
            # above. Without this, a user with Tesseract installed-but-not-on-PATH could pass
            # `python -m src.doctor` yet still hit OCR failures specifically when running via the GUI.
            ocr_engine = OCREngine(tesseract_cmd=self._cfg.tesseract_cmd)

            # Phase 15 (2026-08-11, docs/DECISIONS.md): ported into the GUI path in the SAME pass as
            # main.py this time, per the CLI/GUI-parity lesson from TESSERACT_CMD/AUTO_APPROVE_EXTERNAL/
            # EXECUTION_MODE above -- not left as a follow-up fix to be found missing later.
            operational_limits = OperationalLimits(
                max_cost_usd=self._cfg.max_cost_usd,
                max_wall_clock_seconds=self._cfg.max_wall_clock_seconds,
                max_concurrent_tasks=self._cfg.max_concurrent_tasks,
            )

            with PlaywrightDriver(self._cfg.default_chrome_profile, self._cfg.profiles_dir) as driver:
                router = ActionRouter(
                    playwright_driver=driver, mouse_keyboard=mouse_keyboard, ocr_engine=ocr_engine
                )
                orchestrator = Orchestrator(
                    planner=planner,
                    driver=driver,
                    action_router=router,
                    gate=gate,
                    logger=logger,
                    max_steps=self._cfg.max_steps_per_task,
                    mouse_keyboard=mouse_keyboard,
                    replanner=replanner,
                    memory=memory,
                    log_dir=self._cfg.log_dir,
                    operational_limits=operational_limits,
                    concurrency_guard=_CONCURRENCY_GUARD,
                )
                result = orchestrator.run_task(self._instruction)

            memory.close()
            self.task_finished.emit(result)
        except Exception as exc:  # noqa: BLE001 — surfaced to the GUI, not swallowed
            self.task_failed.emit(str(exc))
