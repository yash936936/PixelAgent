# DOCKER.md — Browser-only Docker deployment (Phase 12)

## The limitation, stated upfront

**This image runs PixelAgent's browser-only execution path. Real OS-level desktop
automation — anything with `target_type: "desktop"` (clicking the Start menu, typing into
Notepad, pressing hotkeys) — does not work in this container, and cannot.** A headless
Linux container has no real display for `pyautogui` to control; this isn't a bug to fix,
it's a structural fact about containers. `EXECUTION_MODE=browser_only` (set in
`docker-compose.yml`) makes this an explicit, enforced choice rather than a confusing
runtime failure — `src/config.py` validates the value, and `src/main.py`'s
`_build_desktop_backends()` skips even attempting to construct `MouseKeyboard`, so any
`target_type: "desktop"` step fails immediately with a clear error instead of partway
through a task.

For real desktop automation, either run PixelAgent natively on Windows (`docs/RELEASE.md`'s
installer), or see `docs/PHASES.md`'s Phase 13 (nested-Windows-VM Docker deployment — not
yet built).

## What's verified vs. not

**Not built or run in this project's build environment** — no `docker` binary is available
here (`which docker` returns nothing). The `Dockerfile`/`docker-compose.yml` below are
written correctly per Docker's documented syntax and this project's actual dependencies
(`requirements.txt`), and the `EXECUTION_MODE=browser_only` enforcement they rely on IS
verified (`tests/test_main.py`'s `_build_desktop_backends()` tests, real pytest, real
assertions). But the container image itself — whether it actually builds, whether
Playwright's Chromium actually launches inside it, whether a real task actually completes
— has not been confirmed. Follow the steps below on a machine with Docker installed before
treating this as a working deployment.

## Build and run

```bash
# Build the image
docker compose build

# Set your API key (required — the compose file has no default and will refuse to
# start without it)
export GEMINI_API_KEY="your-real-key"

# Runs the default smoke-test task ("open example.com") end-to-end
docker compose up
```

For a real task, override the default command:

```bash
docker compose run --rm pixel-agent "search for the weather and tell me if it's raining"
```

## What persists across restarts

`docker-compose.yml` mounts two named volumes:

- `pixel_logs` → `/app/logs` — trace logs, screenshots (pruned per `LOG_RETENTION_DAYS`,
  same as any other deployment — see `docs/DECISIONS.md`'s Phase 8 entry)
- `pixel_profiles` → `/app/profiles` — the Chrome profile Playwright launches against,
  and the episodic/semantic memory SQLite databases

Both survive a `docker compose down && docker compose up` (named volumes are only removed
with `docker compose down -v`, an explicit opt-in to actually delete them).

**Encryption-at-rest note:** `src/security/at_rest.py`'s Windows DPAPI encryption
(`docs/DECISIONS.md`'s Phase 8 entry) is Windows-only. Inside this Linux container,
episodic/semantic memory is stored **unencrypted** — `at_rest.py` detects this and prints
a one-time warning, the same graceful degradation it uses in any non-Windows environment.
If the task data in these volumes is sensitive, treat the volume's storage location (the
Docker host's volume driver, typically local disk) as the security boundary instead.

## Approval prompts inside a container

There's no interactive terminal to answer a confirmation-gate prompt inside a detached
container, so `docker-compose.yml` sets `AUTO_APPROVE_EXTERNAL=true` — External-risk steps
are approved automatically, with no prompt shown at all (see `docs/DECISIONS.md`'s
2026-08-01 entry for the full design). **Destructive-risk steps are unaffected regardless**
— that tier's confirm-phrase requirement cannot be bypassed by any config value, container
or not, by design. A task that reaches a Destructive-risk step inside this container will
still block and wait for a confirm phrase that can never arrive over a non-interactive
`docker compose up`/`run` — if your task might do something destructive, run it with
`docker compose run -it` (interactive) instead, or expect it to hang at that step.

## Health/readiness

No dedicated healthcheck is defined — PixelAgent is a one-shot task runner, not a
long-running service with a natural "ready" state to probe. `docker compose up`'s exit
code (0 on `status: "done"`, non-zero on `status: "error"`) is the signal to check for
scripted/CI usage.

## Smoke test checklist (run once Docker is available)

1. `docker compose build` completes without error.
2. `docker compose up` (with `GEMINI_API_KEY` set) completes the default "open example.com"
   task with `status: "done"` in the printed output.
3. `docker compose run --rm pixel-agent "click a target_type=desktop button"` (a
   deliberately desktop-targeting instruction) fails immediately with a clear
   `UnsupportedTargetType`-style error, not a confusing pyautogui/display crash — confirms
   `EXECUTION_MODE=browser_only` is actually being enforced inside the running container,
   not just validated in isolation by the test suite.
4. `docker compose down && docker compose up` again — confirm the second run's trace log
   in the `pixel_logs` volume includes both runs' logs (not wiped), and any episodic memory
   from the first run is available for replay in the second.
