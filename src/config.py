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

    # Browser
    default_chrome_profile: str = "Default"
    profiles_dir: Path = field(default_factory=lambda: Path("./profiles"))

    # Loop control (see docs/TRD.md §3.1)
    max_steps_per_task: int = 40

    # Logging / observability
    log_dir: Path = field(default_factory=lambda: Path("./logs"))
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    def ensure_dirs(self) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def load(env_path: str | None = None) -> Config:
    """Loads config from environment variables (optionally from a .env file).

    Required env vars:
      GEMINI_API_KEY

    Optional env vars:
      LLM_MODEL, DEFAULT_CHROME_PROFILE, PROFILES_DIR, MAX_STEPS_PER_TASK,
      LOG_DIR, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
    """
    load_dotenv(env_path)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Create a .env file (see .env.example) "
            "or export it in your shell before running Pixel. Get a free key at "
            "https://aistudio.google.com/apikey"
        )

    cfg = Config(
        gemini_api_key=api_key,
        llm_model=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
        default_chrome_profile=os.environ.get("DEFAULT_CHROME_PROFILE", "Default"),
        profiles_dir=Path(os.environ.get("PROFILES_DIR", "./profiles")),
        max_steps_per_task=int(os.environ.get("MAX_STEPS_PER_TASK", "40")),
        log_dir=Path(os.environ.get("LOG_DIR", "./logs")),
        langfuse_public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
        langfuse_secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
    )
    cfg.ensure_dirs()
    return cfg
