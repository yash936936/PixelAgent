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
    llm_model: str = "gemini-2.5-flash"

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
      TESSERACT_CMD, AUTO_APPROVE_EXTERNAL
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

    cfg = Config(
        gemini_api_key=api_key,
        llm_model=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
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
    )
    cfg.ensure_dirs()
    return cfg
