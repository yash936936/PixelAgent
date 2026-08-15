"""
Single source of config truth for the whole project.
Every other module reads settings from a Config instance produced by load() —
nothing else hardcodes config values. See docs/PHASES.md Part 1.1.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    # LLM
    gemini_api_key: str
    llm_model: str = "gemini-3.5-flash-lite"

    # Phase 4 (optional): swap-in a cheaper local/fine-tuned planning model
    # for routine steps instead of the hosted Gemini API. Never replaces the
    # Brain's safety behavior (risk classification, confirmation gate) --
    # those live in orchestrator.py/risk_classifier.py, independent of which
    # planner backend is selected here. See docs/TRD.md §6 and
    # docs/PHASES.md Phase 4.
    planner_backend: str = "hosted"  # "hosted" | "local"
    local_planner_endpoint: str | None = None  # e.g. "http://localhost:11434/api/generate"

    # Track B (docs/DECISIONS.md 2026-07-12): a SEPARATE, independently
    # trained/versioned/rolled-back model for risk/boundary judgment,
    # additive on top of risk_classifier.py's keyword floor and
    # boundary_guard.py's hard-boundary check -- never a replacement for
    # either. Deliberately its own config block, distinct from
    # planner_backend/local_planner_endpoint above, so the two models can be
    # swapped independently (see src/brain/risk_model_backend.py's
    # docstring for the full rationale, and eval/README.md for the
    # mandatory eval-gate before enabling this in production).
    #
    # "semantic" (added 2026-08-01, live-wired Phase 6) is a fourth option:
    # SemanticRiskJudge, a zero-dependency char-n-gram similarity judge --
    # no network/GPU/endpoint required, unlike "hosted"/"local". It is NOT
    # a substitute for a real trained model and does not need or use the
    # eval/README.md deployment gate that "local" does (see
    # risk_model_backend.py's SemanticRiskJudge docstring for why); it's
    # safe to enable by default-adjacent, since it fails open to "no
    # opinion" exactly like every other backend here.
    risk_model_backend: str = "none"  # "none" | "hosted" | "local" | "semantic"
    local_risk_model_endpoint: str | None = None  # e.g. "http://localhost:11435/api/generate"

    # Browser
    default_chrome_profile: str = "Default"
    profiles_dir: Path = field(default_factory=lambda: Path("./profiles"))

    # Loop control (see docs/TRD.md §3.1)
    max_steps_per_task: int = 40

    # Logging / observability
    log_dir: Path = field(default_factory=lambda: Path("./logs"))
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    # Perception (Phase 7 prep, 2026-08-01): explicit path to the Tesseract
    # binary, for the common case where it's installed but not on PATH --
    # src/doctor.py's Tesseract check surfaces exactly this failure mode.
    # None (the default) means OCREngine relies on PATH as before.
    tesseract_cmd: str | None = None

    # Confirmation gate (2026-08-01, docs/DECISIONS.md): added per an
    # explicit user request after finding that approving in a terminal
    # steals OS focus from the actual target app, which then goes to the
    # background and can cause the NEXT step to act on the wrong window.
    # When True, EXTERNAL-risk steps are approved with no prompt shown at
    # all -- see ConfirmationGate's docstring. Deliberately does NOT apply
    # to Risk.DESTRUCTIVE regardless of this setting; that gate's confirm
    # phrase requirement is non-negotiable, the same way boundary_guard.py's
    # hard boundaries can't be disabled by any config value. Defaults to
    # False -- this trades a real safety check for convenience, so it must
    # be an explicit, deliberate opt-in, never a silent default.
    auto_approve_external: bool = False

    # Gemini rate-limit backoff tuning (2026-08-01, docs/DECISIONS.md): found
    # live that the original hardcoded 3-attempt/uncapped-backoff retry could
    # compound into 10+ minutes of total wait on a heavily-throttled
    # free-tier key. Defaults to a much faster-failing tradeoff (2 attempts,
    # capped at 20s) than the original; set RATE_LIMIT_MAX_ATTEMPTS=1 to
    # disable the retry entirely and see rate-limit errors immediately, or
    # raise these if you're on a higher-quota plan and prefer the agent to
    # patiently ride out rate limits instead.
    rate_limit_max_attempts: int = 2
    rate_limit_max_backoff_seconds: float | None = 20.0

    # Retention (2026-08-02, Phase 8, docs/DECISIONS.md): trace logs (.jsonl)
    # and screenshots (.png) in log_dir older than this many days are
    # deleted at process startup. Screenshots are the highest-risk artifact
    # here (full-frame captures), so indefinite retention was deliberately
    # not the default. <= 0 disables pruning entirely.
    log_retention_days: int = 14

    # Deployment mode (2026-08-02, Phase 12, docs/DECISIONS.md): "full_desktop"
    # (default, unchanged behavior) attempts real OS-level mouse/keyboard
    # control and degrades gracefully with a warning if unavailable.
    # "browser_only" is an explicit, declared choice -- used by the Docker
    # image (Dockerfile/docker-compose.yml), where desktop control is not
    # just accidentally missing a display, it's structurally impossible
    # inside a headless Linux container. Skips even attempting to construct
    # MouseKeyboard, giving a clearer startup message than the generic
    # "unavailable" warning, and every target_type="desktop" step fails
    # immediately and explicitly rather than mid-task.
    execution_mode: str = "full_desktop"

    # Operational safety limits (2026-08-11, Phase 15, docs/DECISIONS.md):
    # hard ceilings BEYOND max_steps_per_task above -- a task that's
    # technically making step-by-step progress can still run too long or
    # cost too much in aggregate, which max_steps_per_task alone doesn't
    # catch (a task that keeps needing replans, or an unusually verbose
    # instruction, can rack up many cheap-looking steps that still add up).
    # All three are independently optional; see
    # src/observability/operational_limits.py's OperationalLimits docstring
    # for exactly what each does and doesn't cover (max_wall_clock_seconds
    # in particular is a COOPERATIVE check, not a preemptive kill -- see
    # that module's WallClockGuard docstring). None/unset for cost and
    # wall-clock means "no limit", matching this project's existing
    # opt-in-only convention for every other safety/behavior tradeoff
    # (auto_approve_external, log_retention_days, etc. all ship with an
    # explicit, safe default rather than an implicit one). max_concurrent_tasks
    # defaults to 1, not unlimited, since this project has never had an
    # explicit multi-task guard before this phase (see docs/STATUS.md's
    # standing "no multi-user/concurrency model" known gap) -- 1 preserves
    # today's real, if previously unenforced, single-task-at-a-time usage
    # pattern rather than silently opening up concurrent runs no one has
    # tested against.
    max_cost_usd: float | None = None
    max_wall_clock_seconds: float | None = None
    max_concurrent_tasks: int = 1

    def ensure_dirs(self) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def load(env_path: str | None = None) -> Config:
    """Loads config from environment variables (optionally from a .env file).

    Required env vars:
      GEMINI_API_KEY

    Optional env vars:
      LLM_MODEL, PLANNER_BACKEND, LOCAL_PLANNER_ENDPOINT, RISK_MODEL_BACKEND,
      LOCAL_RISK_MODEL_ENDPOINT, DEFAULT_CHROME_PROFILE,
      PROFILES_DIR, MAX_STEPS_PER_TASK, LOG_DIR, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
      TESSERACT_CMD, AUTO_APPROVE_EXTERNAL, RATE_LIMIT_MAX_ATTEMPTS, RATE_LIMIT_MAX_BACKOFF_SECONDS,
      LOG_RETENTION_DAYS, EXECUTION_MODE, MAX_COST_USD, MAX_WALL_CLOCK_SECONDS, MAX_CONCURRENT_TASKS
    """
    load_dotenv(env_path)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
            "or export it in your shell before running Pixel. Get a free key at "
            "https://aistudio.google.com/apikey"
        )

    planner_backend = os.environ.get("PLANNER_BACKEND", "hosted").strip().lower()
    if planner_backend not in ("hosted", "local"):
        raise RuntimeError(
            f"PLANNER_BACKEND must be 'hosted' or 'local', got {planner_backend!r}."
        )

    risk_model_backend = os.environ.get("RISK_MODEL_BACKEND", "none").strip().lower()
    if risk_model_backend not in ("none", "hosted", "local", "semantic"):
        raise RuntimeError(
            f"RISK_MODEL_BACKEND must be 'none', 'hosted', 'local', or 'semantic', got "
            f"{risk_model_backend!r}. 'none' (the default) keeps the keyword-only "
            "risk_classifier.py/boundary_guard.py floor as the sole risk signal -- see "
            "eval/README.md before setting this to 'local'. 'semantic' needs no endpoint "
            "and no eval gate (see risk_model_backend.py's SemanticRiskJudge docstring)."
        )

    execution_mode = os.environ.get("EXECUTION_MODE", "full_desktop").strip().lower()
    if execution_mode not in ("full_desktop", "browser_only"):
        raise RuntimeError(
            f"EXECUTION_MODE must be 'full_desktop' or 'browser_only', got {execution_mode!r}. "
            "'full_desktop' (the default) is unchanged prior behavior. 'browser_only' is for "
            "the Docker deployment (Phase 12, docs/DECISIONS.md) -- an explicit, declared choice "
            "for environments (e.g. a headless Linux container) where real OS-level desktop "
            "control is structurally impossible, not just accidentally unavailable."
        )

    # Phase 15 (2026-08-11): MAX_COST_USD / MAX_WALL_CLOCK_SECONDS parse to
    # None (no limit) when unset or explicitly "none" -- same pattern
    # RATE_LIMIT_MAX_BACKOFF_SECONDS already established just above, kept
    # consistent rather than inventing a second convention for "no limit".
    def _parse_optional_float(env_name: str) -> float | None:
        raw = os.environ.get(env_name, "").strip().lower()
        if raw in ("", "none"):
            return None
        try:
            return float(raw)
        except ValueError:
            raise RuntimeError(
                f"{env_name} must be a number or unset/'none' for no limit, got {raw!r}."
            )

    max_cost_usd = _parse_optional_float("MAX_COST_USD")
    max_wall_clock_seconds = _parse_optional_float("MAX_WALL_CLOCK_SECONDS")

    max_concurrent_raw = os.environ.get("MAX_CONCURRENT_TASKS", "1").strip()
    try:
        max_concurrent_tasks = int(max_concurrent_raw)
    except ValueError:
        raise RuntimeError(
            f"MAX_CONCURRENT_TASKS must be an integer, got {max_concurrent_raw!r}."
        )
    if max_concurrent_tasks < 1:
        raise RuntimeError(
            f"MAX_CONCURRENT_TASKS must be >= 1, got {max_concurrent_tasks}. "
            "There is currently no way to express 'unlimited' for this setting -- "
            "see src/observability/operational_limits.py's TaskConcurrencyGuard if "
            "that's genuinely needed later."
        )

    cfg = Config(
        gemini_api_key=api_key,
        llm_model=os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite"),
        planner_backend=planner_backend,
        local_planner_endpoint=os.environ.get("LOCAL_PLANNER_ENDPOINT"),
        risk_model_backend=risk_model_backend,
        local_risk_model_endpoint=os.environ.get("LOCAL_RISK_MODEL_ENDPOINT"),
        default_chrome_profile=os.environ.get("DEFAULT_CHROME_PROFILE", "Default"),
        profiles_dir=Path(os.environ.get("PROFILES_DIR", "./profiles")),
        max_steps_per_task=int(os.environ.get("MAX_STEPS_PER_TASK", "40")),
        log_dir=Path(os.environ.get("LOG_DIR", "./logs")),
        langfuse_public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
        tesseract_cmd=os.environ.get("TESSERACT_CMD") or None,
        auto_approve_external=os.environ.get("AUTO_APPROVE_EXTERNAL", "false").strip().lower() == "true",
        rate_limit_max_attempts=int(os.environ.get("RATE_LIMIT_MAX_ATTEMPTS", "2")),
        rate_limit_max_backoff_seconds=(
            None
            if os.environ.get("RATE_LIMIT_MAX_BACKOFF_SECONDS", "").strip().lower() == "none"
            else float(os.environ.get("RATE_LIMIT_MAX_BACKOFF_SECONDS", "20"))
        ),
        log_retention_days=int(os.environ.get("LOG_RETENTION_DAYS", "14")),
        execution_mode=execution_mode,
        max_cost_usd=max_cost_usd,
        max_wall_clock_seconds=max_wall_clock_seconds,
        max_concurrent_tasks=max_concurrent_tasks,
    )
    cfg.ensure_dirs()
    return cfg
