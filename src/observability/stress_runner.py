"""
src/observability/stress_runner.py — Phase 15's real multi-hour stress run.

Honest scope, same as tests/brain/test_orchestrator_stress.py (which this module
is the long-running sibling of, not a duplicate): the CI-friendly pytest version
runs ~300 fast synthetic iterations in seconds and catches Python-level resource
leaks (thread/RSS/concurrency-slot growth, log-file collisions). It does NOT
exercise real Playwright/Chromium or real OS-level mouse/keyboard, so it cannot
by itself satisfy Phase 15's actual success criterion ("survives a multi-hour
stress run... without a memory leak, orphaned process, or runaway cost").

THIS module is what actually gets run for that real, multi-hour, real-hardware
pass -- but it still ships with the same lightweight fakes as its default, so it
can be smoke-tested anywhere (including this sandboxed environment) before ever
being pointed at real components. To run the REAL stress test Phase 15 still
needs:
    1. On real Windows hardware, with a real Chromium/Playwright install.
    2. Swap `_build_stress_orchestrator()`'s fake `planner`/`driver` below for
       real ones (`HostedLLMPlanner`, `PlaywrightDriver` -- see src/main.py for
       how those get constructed from config.py in normal operation).
    3. Run for hours: `python -m src.observability.stress_runner --hours 4`.
    4. Watch for real OS-level signals this module cannot see from Python alone
       (orphaned `chrome.exe`/`chromedriver.exe` processes in Task Manager after
       the run ends, actual system RAM climbing beyond what ru_maxrss reports,
       GPU/handle exhaustion) -- these need a human watching the real machine,
       not just this script's own numbers.

Usage (synthetic/smoke-test mode, safe to run anywhere):
    python -m src.observability.stress_runner --iterations 500
    python -m src.observability.stress_runner --minutes 5

Prints periodic progress and writes a JSON summary at the end.
"""
from __future__ import annotations

import argparse
import ctypes
import gc
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from src.action.playwright_driver import PlaywrightDriver
from src.brain.orchestrator import Orchestrator
from src.brain.planner import HostedLLMPlanner
from src.brain.risk_classifier import Risk
from src.confirmation.gate import ConfirmationGate, GateDecision
from src.observability.logger import Logger, prune_old_logs
from src.observability.operational_limits import (
    OperationalLimitExceeded,
    OperationalLimits,
    TaskConcurrencyGuard,
)

# The single fixed instruction every task runs under --real. Deliberately
# not configurable (see module docstring "REAL MODE SAFETY") -- narrow and
# read-only by construction, so nothing riskier can get swapped in for an
# unattended multi-hour run.
_REAL_MODE_INSTRUCTION = (
    "Take a screenshot of the current screen and describe what you see. "
    "Do not click, type, navigate, or take any other action."
)


def _deny_all_prompt_fn(step, risk, context=None) -> GateDecision:
    """ConfirmationGate's prompt_fn for --real mode. Auto-denies every
    External/Destructive step rather than blocking on stdin (which would
    hang forever with nobody there to answer) or auto-approving (which
    would be genuinely unsafe for an unattended multi-hour run against
    real APIs/a real browser). raw_user_input identifies this function by
    name so a denied-step trace log entry is traceable back to the stress
    runner, not confused with a real human's denial."""
    return GateDecision(verdict="denied", raw_user_input="denied by stress_runner._deny_all_prompt_fn")


def _current_rss_kb() -> int:
    """Cross-platform current process RSS in KB.

    Real bug found live (2026-08-17, docs/DECISIONS.md): the original version
    of this module used the stdlib `resource` module directly, which is
    POSIX-only -- it doesn't exist on Windows at all, so `import resource`
    crashed immediately on the actual target platform this whole project is
    built for, before a single stress iteration ever ran. Never caught here
    because this sandboxed dev environment is Linux; only surfaced once this
    module was actually run on real Windows hardware, exactly the kind of gap
    this stress run exists to catch, just one level earlier than intended.

    Fixed with a real per-platform implementation rather than adding a new
    pip dependency (e.g. psutil) for one figure:
      - POSIX (Linux/macOS): `resource.getrusage(RUSAGE_SELF).ru_maxrss`,
        imported lazily inside this branch so the module still loads cleanly
        on Windows, where the import itself would fail.
      - Windows: `GetProcessMemoryInfo` via `ctypes` against `psapi.dll`,
        stdlib-only, no extra dependency -- returns the current working set
        size (current resident memory), not a high-water mark like POSIX's
        ru_maxrss. This is a real, meaningful difference (see this function's
        callers) but still catches the thing that matters: memory that never
        comes back down across many iterations.

    Second real bug found live on Windows (2026-08-17, docs/DECISIONS.md):
    the first version of the Windows branch called GetCurrentProcess() and
    GetProcessMemoryInfo() with no argtypes/restype declared. ctypes
    defaults undeclared return values to a 32-bit c_int -- so
    GetCurrentProcess()'s real return value (a 64-bit pseudo-handle,
    -1 / 0xFFFFFFFFFFFFFFFF on Win64) got silently truncated to a 32-bit
    value before ever reaching GetProcessMemoryInfo(), which then failed
    outright (returned 0/FALSE) on a corrupted handle. Fixed by declaring
    explicit argtypes/restype using ctypes.wintypes, the actual documented
    fix ctypes' own docs call for when calling any WinAPI function -- not
    optional boilerplate.
    """
    if sys.platform == "win32":
        import ctypes.wintypes as wintypes

        kernel32 = ctypes.windll.kernel32
        psapi = ctypes.windll.psapi

        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.GetCurrentProcess.argtypes = []

        # PROCESS_MEMORY_COUNTERS.WorkingSetSize, in bytes -- current, not
        # peak. GetCurrentProcess() returns a pseudo-handle valid for the
        # calling process, no CloseHandle needed per Win32 docs.
        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ProcessMemoryCounters),
            wintypes.DWORD,
        ]

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            # ctypes.WinError() (not ctypes.get_last_error(), which needs
            # use_last_error=True at DLL-load time to be reliable, unset
            # here since ctypes.windll doesn't set it) -- WinError() calls
            # the real Win32 GetLastError() itself and raises an OSError
            # with Windows' own real error message, which is far more
            # actionable than a bare "failed" string.
            raise ctypes.WinError()
        return counters.WorkingSetSize // 1024

    import resource  # POSIX-only; safe here since sys.platform != "win32"

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _close_if_possible(obj) -> None:
    """Best-effort close for any real resource (sqlite-backed stores, DB
    connections, etc.) that might be wired into a real (non-fake)
    orchestrator. Fakes mode has nothing to close, so this is a no-op there
    -- added defensively for real-mode runs where a real MemoryAPI /
    EpisodicStore holds an open sqlite3 connection to a file under the
    temp log_dir. Without this, Windows (unlike POSIX) refuses to delete a
    file that still has an open handle, which is exactly the
    'PermissionError: WinError 32 ... episodic_memory.db' failure seen
    during real-mode testing on 2026-08-19 -- see docs/DECISIONS.md.
    """
    close = getattr(obj, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass  # best-effort only; never let cleanup itself crash the run


def _build_stress_orchestrator(log_dir: Path, guard: TaskConcurrencyGuard) -> Orchestrator:
    """Default fakes, same shape as tests/brain/test_orchestrator_stress.py.
    Swap this out for real components (see this module's docstring) before a
    real multi-hour hardware run -- left as fakes here so this script is
    always safe to smoke-test in any environment, including one with no
    Chromium/Gemini access at all. IMPORTANT for real-mode swaps: if you wire
    a real MemoryAPI/EpisodicStore into the Orchestrator built here, this
    function's caller (run_stress) will call _close_if_possible() on the
    orchestrator's memory object each iteration -- make sure Orchestrator or
    MemoryAPI exposes a .close() (or a .memory/._memory attribute pointing
    at something that does) or the fix below can't reach it."""
    planner = MagicMock()
    planner.next_step.side_effect = [{"action": "done"}]
    planner.last_call_cost = 0.0001

    driver = MagicMock()
    driver.is_launched = False

    action_router = MagicMock()
    action_router.execute.return_value = {"status": "executed"}

    gate = MagicMock()
    logger = Logger(log_dir)

    risk_classifier = MagicMock()
    risk_classifier.classify_with_confidence.return_value = (Risk.LOCAL, True)
    risk_classifier.needs_confirmation.return_value = False

    return Orchestrator(
        planner=planner,
        driver=driver,
        action_router=action_router,
        gate=gate,
        logger=logger,
        max_steps=100,
        risk_classifier=risk_classifier,
        concurrency_guard=guard,
        log_dir=log_dir,
    )


def _build_real_stress_orchestrator(
    cfg, log_dir: Path, guard: TaskConcurrencyGuard, headless: bool = True
) -> tuple[PlaywrightDriver, Orchestrator]:
    """Real (non-fake) planner/driver/gate/Orchestrator wiring for --real
    mode, matching src/main.py's own construction as closely as possible
    (see main.py's main() for the reference wiring this mirrors) with two
    deliberate differences required for an unattended run:
      - gate uses _deny_all_prompt_fn, not console_prompt (would block on
        stdin forever) or auto_approve_external=True (unsafe unattended).
      - the instruction every task runs is _REAL_MODE_INSTRUCTION, fixed
        and read-only, not whatever's passed on the command line.

    Returns (driver, orchestrator) rather than just the orchestrator so the
    caller can manage the driver's lifecycle (real Chromium launch/close)
    explicitly per iteration -- deliberately opening/closing fresh every
    task rather than once for the whole run, since repeated launch/close is
    exactly where an orphaned-process bug would show up (see module
    docstring point 4).
    """
    planner = HostedLLMPlanner(
        api_key=cfg.gemini_api_key,
        model=cfg.llm_model,
        rate_limit_max_attempts=cfg.rate_limit_max_attempts,
        rate_limit_max_backoff_seconds=cfg.rate_limit_max_backoff_seconds,
    )
    driver = PlaywrightDriver(cfg.default_chrome_profile, cfg.profiles_dir, headless=headless)

    # Real bug found live (2026-08-27, docs/DECISIONS.md): every single real
    # task was silently failing at step 1 -- "target_type='desktop' requires
    # a MouseKeyboard backend -- none was configured" -- because this
    # function previously hardcoded mouse_keyboard=None. _REAL_MODE_INSTRUCTION
    # asks for a desktop screenshot, which needs exactly this backend. Fixed
    # by using the same _build_desktop_backends() helper src/main.py itself
    # uses for real runs, rather than a stress-runner-specific shortcut that
    # diverged from how this app actually launches in practice.
    from src.main import _build_desktop_backends

    mouse_keyboard, ocr_engine = _build_desktop_backends(cfg)

    action_router_module = __import__("src.action.action_router", fromlist=["ActionRouter"])
    router = action_router_module.ActionRouter(
        playwright_driver=driver, mouse_keyboard=mouse_keyboard, ocr_engine=ocr_engine
    )
    gate = ConfirmationGate(prompt_fn=_deny_all_prompt_fn, auto_approve_external=False)
    logger = Logger(log_dir)
    operational_limits = OperationalLimits(
        max_cost_usd=cfg.max_cost_usd,
        max_wall_clock_seconds=cfg.max_wall_clock_seconds,
        max_concurrent_tasks=cfg.max_concurrent_tasks,
    )

    orch = Orchestrator(
        planner=planner,
        driver=driver,
        action_router=router,
        gate=gate,
        logger=logger,
        max_steps=cfg.max_steps_per_task,
        log_dir=log_dir,
        operational_limits=operational_limits,
        concurrency_guard=guard,
    )
    return driver, orch


def run_stress(
    log_root: Path,
    iterations: int | None = None,
    duration_seconds: float | None = None,
    retention_days: int = 14,
    progress_every: int = 50,
    real: bool = False,
    headless: bool = True,
    checkpoint_path: Path | None = None,
    stop_after_consecutive_errors: int | None = None,
) -> dict:
    """Runs tasks back-to-back until either `iterations` is reached or
    `duration_seconds` elapses (whichever is given -- if both are given,
    stops at whichever comes first). Returns a summary dict, same one
    written to the JSON file by _main() below.

    Calls prune_old_logs() periodically, same as a real long-running process
    would at natural checkpoints, rather than only once at startup -- a real
    multi-hour run needs pruning to actually keep the log directory bounded
    DURING the run, not just before it starts.
    """
    cfg = None
    if real:
        import src.config as config_module

        # Fails loudly here, same RuntimeError config.load() itself raises
        # when GEMINI_API_KEY is missing -- not caught/swallowed, since a
        # --real run with no real config is a startup-time error, not
        # something to silently fall back from.
        cfg = config_module.load()

    guard = TaskConcurrencyGuard(max_concurrent=1)
    gc.collect()
    rss_start_kb = _current_rss_kb()
    thread_start = threading.active_count()
    start_time = time.monotonic()

    completed = 0
    limit_stops = 0
    errors = 0
    consecutive_errors = 0
    i = 0
    while True:
        if iterations is not None and i >= iterations:
            break
        if duration_seconds is not None and (time.monotonic() - start_time) >= duration_seconds:
            break

        driver = None
        try:
            if real:
                driver, orch = _build_real_stress_orchestrator(cfg, log_root, guard, headless=headless)
                with driver:
                    result = orch.run_task(_REAL_MODE_INSTRUCTION)
            else:
                orch = _build_stress_orchestrator(log_root, guard)
                result = orch.run_task(f"stress task {i}")
            status = result.get("status")
            if status == "operational_limit_exceeded":
                limit_stops += 1
            elif status == "error":
                # Real bug found live (2026-08-27, docs/DECISIONS.md): a
                # task can complete its call to orch.run_task() without
                # raising, yet still represent a real per-task failure --
                # Orchestrator sets outcome_status="error" (not an
                # exception) when a step errors out internally. This was
                # previously falling into the "anything else counts as
                # completed" branch below, silently miscounting every
                # failed real task as a success -- masking a real,
                # reproducible wiring bug (missing MouseKeyboard backend)
                # for an entire ~4-hour run.
                errors += 1
                consecutive_errors += 1
            else:
                completed += 1
                consecutive_errors = 0
        except OperationalLimitExceeded:
            limit_stops += 1
            consecutive_errors = 0
        except Exception as exc:  # noqa: BLE001 - a real stress run must keep going and report, not crash
            # Real gap found live (2026-08-27, docs/DECISIONS.md): this
            # branch previously just incremented `errors` with no record
            # of WHAT failed. A real run with 357/394 iterations erroring
            # had no diagnosable trace of the actual cause anywhere --
            # only 43 of 394 iterations even got a Logger entry, meaning
            # most failures happened before orch.run_task() ever started
            # writing (almost certainly PlaywrightDriver launch itself --
            # a real, repeated, silent failure with zero visibility).
            # Printing every exception's type+message here is cheap and
            # exactly what a real multi-hour run needs to be diagnosable
            # after the fact, without relying on per-task logs that may
            # not exist for this class of failure.
            print(
                f"[error] iteration {i}: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
            try:
                (log_root / "errors.log").open("a", encoding="utf-8").write(
                    f"[iter {i}] {type(exc).__name__}: {exc}\n"
                )
            except OSError:
                pass  # best-effort only; never let error logging crash the run
            errors += 1
            consecutive_errors += 1
        finally:
            # Close any real per-iteration resource (e.g. a real-mode
            # MemoryAPI/EpisodicStore's sqlite3 connection) before this
            # orchestrator goes out of scope, so nothing holds an open file
            # handle into log_root by the time cleanup runs at the end of
            # the script. No-op in default fakes mode.
            _close_if_possible(getattr(orch, "_memory", None))

        if guard.active_count != 0:
            # A leaked slot here means every subsequent task would fail --
            # stop immediately rather than silently burning the rest of the
            # run against a guard that's already broken.
            print(
                f"FATAL: concurrency slot leaked after iteration {i} "
                f"(active_count={guard.active_count}) -- stopping early.",
                file=sys.stderr,
            )
            break

        if (
            stop_after_consecutive_errors is not None
            and consecutive_errors >= stop_after_consecutive_errors
        ):
            # Real-world case this exists for: a Gemini quota fully
            # exhausted partway through a long run (observed 2026-08-21 --
            # `completed` froze while `errors` climbed for over 2 hours
            # straight after the daily quota ran out). Continuing to burn
            # through thousands of instant-fail iterations tests nothing
            # new and just wastes wall-clock time -- stop and report
            # honestly instead of pretending a long `errors` streak is
            # still useful stress-test data.
            print(
                f"STOPPING EARLY: {consecutive_errors} consecutive errors after iteration {i} "
                f"-- likely a fully exhausted API quota or a persistent failure, not something "
                f"more iterations will fix. See the errors above/in logs for the actual cause.",
                file=sys.stderr,
            )
            break

        i += 1
        if i % progress_every == 0:
            elapsed = time.monotonic() - start_time
            gc.collect()
            rss_now_kb = _current_rss_kb()
            print(
                f"[{elapsed:8.1f}s] iter={i} completed={completed} "
                f"limit_stops={limit_stops} errors={errors} "
                f"rss={rss_now_kb / 1024:.1f}MB threads={threading.active_count()}"
            )
            prune_old_logs(log_root, retention_days)

            if checkpoint_path is not None:
                # Written every progress_every iterations so an unplanned
                # interruption (closed terminal, sleep, crash) still leaves
                # real, current numbers on disk instead of losing the whole
                # run's data -- the exact gap that lost a ~2.9-hour run's
                # results on 2026-08-21. Deliberately best-effort: a
                # checkpoint-write failure must never crash the run itself.
                try:
                    checkpoint_path.write_text(
                        json.dumps(
                            {
                                "checkpoint": True,
                                "iterations_run": i,
                                "completed": completed,
                                "limit_stops": limit_stops,
                                "errors": errors,
                                "consecutive_errors": consecutive_errors,
                                "elapsed_seconds": elapsed,
                                "rss_now_kb": rss_now_kb,
                                "thread_count_now": threading.active_count(),
                            },
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                except OSError:
                    pass

    gc.collect()
    rss_end_kb = _current_rss_kb()
    thread_end = threading.active_count()
    remaining_files = prune_old_logs(log_root, retention_days)

    return {
        "iterations_run": i,
        "completed": completed,
        "limit_stops": limit_stops,
        "errors": errors,
        "duration_seconds": time.monotonic() - start_time,
        "rss_start_kb": rss_start_kb,
        "rss_end_kb": rss_end_kb,
        "rss_growth_kb": rss_end_kb - rss_start_kb,
        "thread_count_start": thread_start,
        "thread_count_end": thread_end,
        "thread_leak": thread_end - thread_start,
        "final_prune_deleted": remaining_files,
        "concurrency_guard_clean": guard.active_count == 0,
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=None, help="Number of tasks to run.")
    parser.add_argument("--minutes", type=float, default=None, help="Duration to run, in minutes.")
    parser.add_argument("--hours", type=float, default=None, help="Duration to run, in hours.")
    parser.add_argument(
        "--log-dir", type=str, default=None,
        help="Directory for real task logs during the run. Defaults to a temp dir "
             "(smoke-test mode) -- pass a real path for an actual long run so the "
             "logs survive after this process exits.",
    )
    parser.add_argument("--out", type=str, default="stress_run_summary.json")
    parser.add_argument(
        "--real", action="store_true",
        help="Use real HostedLLMPlanner + PlaywrightDriver instead of fakes. "
             "Makes real Gemini API calls and launches a real Chromium browser. "
             "See this module's docstring, 'REAL MODE SAFETY', for full detail.",
    )
    parser.add_argument(
        "--headless", dest="headless", action="store_true", default=True,
        help="Run the real browser headless (default).",
    )
    parser.add_argument(
        "--visible", dest="headless", action="store_false",
        help="Run the real browser visibly (headless=False) -- for --real mode only.",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip the interactive confirmation prompt before a --real run "
             "(for scripting only).",
    )
    parser.add_argument(
        "--checkpoint", type=str, default=None,
        help="Path to write a live progress checkpoint every --progress-every "
             "iterations, so an interrupted run (closed terminal, sleep, crash) "
             "doesn't lose all its data. Written throughout the run, not just at "
             "the end. Defaults to '<out>.checkpoint.json' if --real is set and "
             "this isn't given, since a real run is exactly the case an "
             "interruption is costly for.",
    )
    parser.add_argument(
        "--stop-after-consecutive-errors", type=int, default=None,
        help="Stop the run early if this many task attempts in a row all error "
             "(e.g. a fully exhausted API quota) -- avoids burning hours of "
             "wall-clock time on iterations that all fail the same way. Defaults "
             "to 100 if --real is set and this isn't given; unset (None) for "
             "fakes mode, where a long error streak would itself be the bug "
             "being tested for.",
    )
    args = parser.parse_args()

    if args.iterations is None and args.minutes is None and args.hours is None:
        args.iterations = 500  # sane smoke-test default

    duration_seconds = None
    if args.hours is not None:
        duration_seconds = args.hours * 3600
    elif args.minutes is not None:
        duration_seconds = args.minutes * 60

    if args.real and not args.yes:
        hours_str = f"{duration_seconds / 3600:.2f}" if duration_seconds is not None else "an unbounded number of"
        print(
            "--real mode will:\n"
            "  - Make real Gemini API calls (spends real quota/money) for every task.\n"
            "  - Launch and close a real Chromium browser per task (headless).\n"
            f"  - Run for approximately {hours_str} hours.\n"
            "  - Auto-deny any External/Destructive-risk step (never blocks on input, "
            "never takes a real risky action unattended).\n"
            "See this module's docstring, 'REAL MODE SAFETY', for full detail."
        )
        confirm = input("Type 'yes' to proceed: ")
        if confirm.strip().lower() != "yes":
            print("Aborted.")
            raise SystemExit(1)

    if args.log_dir is not None:
        log_root = Path(args.log_dir)
        log_root.mkdir(parents=True, exist_ok=True)
        tmp_ctx = None
    else:
        tmp_ctx = tempfile.TemporaryDirectory(prefix="pixel_stress_")
        log_root = Path(tmp_ctx.name)

    print(f"Starting stress run — mode={'real' if args.real else 'fakes'} log_dir={log_root}")

    checkpoint_path = None
    if args.checkpoint is not None:
        checkpoint_path = Path(args.checkpoint)
    elif args.real:
        checkpoint_path = Path(f"{args.out}.checkpoint.json")

    stop_after_consecutive_errors = args.stop_after_consecutive_errors
    if stop_after_consecutive_errors is None and args.real:
        stop_after_consecutive_errors = 100

    if checkpoint_path is not None:
        print(f"Live checkpoint will be written to {checkpoint_path} every {50} iterations.")

    try:
        summary = run_stress(
            log_root,
            iterations=args.iterations,
            duration_seconds=duration_seconds,
            real=args.real,
            headless=args.headless,
            checkpoint_path=checkpoint_path,
            stop_after_consecutive_errors=stop_after_consecutive_errors,
        )
    finally:
        if tmp_ctx is not None:
            # Retry cleanup a few times with a short backoff: on Windows,
            # a file handle can take a moment to release even after
            # _close_if_possible() has run (OS-level flush, AV scan, etc.).
            # This must never mask a real bug -- if it's still locked after
            # retrying, we print exactly which file so it's diagnosable
            # instead of failing with a bare stack trace after a real
            # multi-hour run.
            last_err = None
            for attempt in range(5):
                try:
                    tmp_ctx.cleanup()
                    last_err = None
                    break
                except PermissionError as e:
                    last_err = e
                    gc.collect()
                    time.sleep(1.0)
            if last_err is not None:
                print(
                    f"WARNING: could not clean up temp log dir {log_root} "
                    f"after retrying ({last_err}). The run's own results "
                    f"above/summary JSON are still valid -- this only means "
                    f"the temp directory needs manual deletion. See "
                    f"docs/DECISIONS.md 2026-08-19 entry.",
                    file=sys.stderr,
                )

    print("\n=== Stress run summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary written to {args.out}")

    ok = summary["concurrency_guard_clean"] and summary["errors"] == 0
    if not ok:
        print("\nFAIL: stress run surfaced an issue -- see summary above.", file=sys.stderr)
        raise SystemExit(1)
    print("\nOK: no leaks or errors detected by this script's own checks.")


if __name__ == "__main__":
    _main()
