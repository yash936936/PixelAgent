# PixelAgent — browser-only Docker deployment (Phase 12, docs/DECISIONS.md 2026-08-02)
#
# IMPORTANT: this image runs PixelAgent's BROWSER-ONLY execution path.
# Real OS-level desktop automation (mouse_keyboard.py, target_type="desktop"
# steps) is structurally impossible in a headless Linux container -- there
# is no real display for pyautogui to control. EXECUTION_MODE=browser_only
# below (see docker-compose.yml) makes this an explicit, enforced choice
# (src/config.py validates it, src/main.py's _build_desktop_backends()
# skips even attempting desktop control) rather than a silent runtime
# failure. For real desktop automation, see Phase 13's nested-Windows-VM
# approach or run PixelAgent natively on Windows (Phase 11's installer).
#
# NOT BUILT OR RUN in this project's build environment -- no docker daemon
# is available here (confirmed: `docker` is not on PATH). Written correctly
# per Docker's documented syntax and this project's own actual
# dependencies (requirements.txt), but unverified until built and run on a
# real machine with Docker installed. See docs/DOCKER.md for the
# build/run/smoke-test steps to actually confirm this works.

FROM python:3.12-slim

# tesseract-ocr: the real OCR binary OCREngine calls via pytesseract --
# without this, every OCR-dependent step fails at runtime with a clear
# error (see src/doctor.py's Tesseract check), not silently.
# Playwright's own system dependencies (fonts, libnss3, etc.) are
# installed via `playwright install --with-deps` below rather than
# listed by hand here, since that list is version-specific and
# Playwright's own installer knows exactly what its bundled Chromium
# build needs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium only -- this image never needs pyautogui's desktop-control path
# (EXECUTION_MODE=browser_only), and pyautogui itself would fail to import
# at all without a real display regardless, per src/action/mouse_keyboard.py's
# own graceful degradation.
RUN playwright install --with-deps chromium

COPY src/ ./src/
COPY .env.example .

# Mount points for persistent state across container restarts -- see
# docker-compose.yml's volumes section. Created here so the image has
# correct ownership/permissions before any volume is mounted over them.
RUN mkdir -p /app/logs /app/profiles

ENV EXECUTION_MODE=browser_only
ENV PROFILES_DIR=/app/profiles
ENV LOG_DIR=/app/logs

ENTRYPOINT ["python", "-m", "src.main"]
