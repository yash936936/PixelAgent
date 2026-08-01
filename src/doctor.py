"""
Pre-flight diagnostic tool for Phase 7 (docs/PHASES.md) — the first real
live run on the user's actual Windows machine. Every prior phase's tests
run against mocks; this is the first thing in the project meant to be run
against real hardware, and it deliberately checks readiness WITHOUT
executing a real task, a real click, or a real destructive action.

Run it with:
    python -m src.doctor

Add --live to also make one real, cheap Gemini API call (a single
"reply with OK" prompt) to confirm the API key actually works end-to-end,
not just that it's present and well-formed. Without --live, the Gemini
check only validates config, since a real network call costs money and
this tool should be safe to run repeatedly while debugging environment
setup.

Why this exists: docs/STATUS.md has flagged "zero live validation" since
Phase 5, and Phase 6's DECISIONS.md entry notes none of the semantic-layer
wiring has been exercised against a real Gemini call or a real
confirmation dialog. Rather than let the first live run also be the first
time missing-Tesseract/missing-API-key/no-display failures surface, this
tool front-loads exactly those checks so Phase 7 spends its time
validating the things that can ONLY be validated live (OCR accuracy on
real screenshots, click-coordinate precision, DPI scaling) rather than
re-discovering environment setup problems this tool could have caught in
five seconds.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from src import config


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    #: True if failing this check only limits functionality (e.g. desktop
    #: control unavailable) rather than blocking every task. Mirrors
    #: main.py's own "web-only mode" graceful-degradation philosophy for
    #: MouseKeyboard/OCREngine (see _build_desktop_backends()).
    optional: bool = False


def check_config() -> CheckResult:
    try:
        cfg = config.load()
    except RuntimeError as exc:
        return CheckResult("Config / GEMINI_API_KEY", False, str(exc))
    return CheckResult(
        "Config / GEMINI_API_KEY",
        True,
        f"loaded OK (planner_backend={cfg.planner_backend!r}, "
        f"risk_model_backend={cfg.risk_model_backend!r})",
    )


def check_gemini_live(cfg) -> CheckResult:
    """Only called with --live. Makes one real, minimal API call."""
    try:
        from src.brain.planner import HostedLLMPlanner

        generate_fn = HostedLLMPlanner(api_key=cfg.gemini_api_key, model=cfg.llm_model)._generate_fn
        reply = generate_fn("Reply with exactly: OK", "OK")
        return CheckResult("Gemini API (live call)", True, f"got a response: {reply[:60]!r}")
    except Exception as exc:  # noqa: BLE001 - report any failure, not just network errors
        return CheckResult("Gemini API (live call)", False, f"{type(exc).__name__}: {exc}")


def check_tesseract() -> CheckResult:
    try:
        import pytesseract

        version = pytesseract.get_tesseract_version()
        return CheckResult("Tesseract OCR binary", True, f"found, version {version}")
    except ImportError:
        return CheckResult("Tesseract OCR binary", False, "pytesseract not installed (pip install -r requirements.txt)")
    except Exception as exc:  # noqa: BLE001 - covers TesseractNotFoundError etc.
        return CheckResult(
            "Tesseract OCR binary",
            False,
            f"pytesseract is installed but the Tesseract binary itself was not found on PATH ({exc}). "
            "Install from https://github.com/UB-Mannheim/tesseract/wiki and either add it to PATH or "
            "set OCREngine(tesseract_cmd=...) explicitly.",
        )


def check_playwright_chromium() -> CheckResult:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return CheckResult("Playwright Chromium", True, "launches successfully")
    except ImportError:
        return CheckResult("Playwright Chromium", False, "playwright not installed (pip install -r requirements.txt)")
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "Playwright Chromium",
            False,
            f"{type(exc).__name__}: {exc} -- try running `playwright install chromium`",
        )


def check_desktop_control() -> CheckResult:
    """Optional: MouseKeyboard/pyautogui require a real display. Mirrors
    main.py's _build_desktop_backends(), which already degrades to
    web-only mode rather than failing hard if this is unavailable -- so a
    failure here is reported but never blocks the rest of this tool or a
    browser-only task."""
    try:
        import pyautogui

        width, height = pyautogui.size()
        if width <= 0 or height <= 0:
            return CheckResult(
                "Desktop control (pyautogui + real display)",
                False,
                f"pyautogui imported but reported an invalid screen size ({width}x{height}) -- "
                "no real display detected. Desktop-target-type steps will be unavailable; "
                "browser-only tasks are unaffected.",
                optional=True,
            )
        return CheckResult(
            "Desktop control (pyautogui + real display)",
            True,
            f"real display detected, {width}x{height}",
            optional=True,
        )
    except ImportError:
        return CheckResult(
            "Desktop control (pyautogui + real display)",
            False,
            "pyautogui not installed -- desktop-target-type steps will be unavailable; "
            "browser-only tasks are unaffected.",
            optional=True,
        )
    except Exception as exc:  # noqa: BLE001 - e.g. no X server on Linux
        return CheckResult(
            "Desktop control (pyautogui + real display)",
            False,
            f"{type(exc).__name__}: {exc} -- no real display available. Desktop-target-type steps "
            "will be unavailable; browser-only tasks are unaffected.",
            optional=True,
        )


def check_writable_dirs(cfg) -> CheckResult:
    problems = []
    for label, path in (("profiles_dir", cfg.profiles_dir), ("log_dir", cfg.log_dir)):
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".pixel_doctor_write_test"
            probe.write_text("ok")
            probe.unlink()
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{label} ({path}): {type(exc).__name__}: {exc}")

    if problems:
        return CheckResult("Writable profiles_dir/log_dir", False, "; ".join(problems))
    return CheckResult(
        "Writable profiles_dir/log_dir", True, f"{cfg.profiles_dir} and {cfg.log_dir} both writable"
    )


def check_semantic_layer() -> CheckResult:
    """Sanity check for Phase 6's wiring -- purely local/in-process, so
    this should always pass; a failure here means something is broken in
    the environment's own src/ install, not an external dependency."""
    try:
        from src.brain.risk_model_backend import SemanticRiskJudge

        result = SemanticRiskJudge().judge({"action": "click", "description": "get rid of this permanently"})
        from src.brain.risk_classifier import Risk

        if result != Risk.DESTRUCTIVE:
            return CheckResult(
                "Semantic risk layer (Phase 6)", False, f"expected DESTRUCTIVE, got {result!r}"
            )
        return CheckResult("Semantic risk layer (Phase 6)", True, "SemanticRiskJudge working correctly")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Semantic risk layer (Phase 6)", False, f"{type(exc).__name__}: {exc}")


def run_diagnostics(live: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []

    config_result = check_config()
    results.append(config_result)

    if live and config_result.passed:
        cfg = config.load()
        results.append(check_gemini_live(cfg))

    results.append(check_tesseract())
    results.append(check_playwright_chromium())
    results.append(check_desktop_control())

    if config_result.passed:
        results.append(check_writable_dirs(config.load()))

    results.append(check_semantic_layer())

    return results


def _print_report(results: list[CheckResult]) -> int:
    """Returns a process exit code: 0 if every non-optional check passed,
    1 otherwise. Optional-check failures are shown but never affect the
    exit code, matching main.py's own graceful-degradation behavior for
    desktop control."""
    print("PixelAgent pre-flight diagnostics (Phase 7 readiness check)\n" + "=" * 60)
    blocking_failures = 0
    for r in results:
        icon = "✓" if r.passed else ("⚠" if r.optional else "✗")
        tag = " (optional)" if r.optional else ""
        print(f"{icon} {r.name}{tag}: {r.detail}")
        if not r.passed and not r.optional:
            blocking_failures += 1

    print("=" * 60)
    if blocking_failures:
        print(f"{blocking_failures} blocking check(s) failed. Fix these before attempting a live task.")
        return 1
    print("All required checks passed. Optional warnings above (if any) only limit desktop-target-type steps.")
    return 0


if __name__ == "__main__":
    live_mode = "--live" in sys.argv
    outcomes = run_diagnostics(live=live_mode)
    sys.exit(_print_report(outcomes))
