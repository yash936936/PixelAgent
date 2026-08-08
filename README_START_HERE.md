# What's in this zip

Fixes and documentation from tonight's first real Windows installer build-and-run cycle,
now with all four project docs (`RELEASE.md`, `DECISIONS.md`, `STATUS.md`, `PHASES.md`)
updated to match, per this project's own convention of keeping those in sync.

## Files, and what to do with each

1. **`installer/pixel-agent.iss`** — drop-in replacement for your real
   `installer/pixel-agent.iss`. Contains the 2026-08-06 fixes (`SourceDir`,
   `OutputDir`) plus tonight's fix: the `[Code]` section now writes
   `PLAYWRIGHT_BROWSERS_PATH` into the generated `.env` when the `chromium` component is
   installed, so a fresh install's bundled Playwright actually finds the staged
   Chromium binary instead of crashing on the first browser task.

2. **`docs/RELEASE.md`** — drop-in replacement for your real `docs/RELEASE.md`. Updated
   verified/unverified table (most rows now genuinely `[VERIFIED]`, confirmed live
   tonight), plus a full "Known issues found on first real build" section documenting
   all five bugs and fixes.

3. **`docs/STATUS.md`** — drop-in replacement for your real `docs/STATUS.md`. This is
   the FULL file, not a snippet — I had complete content for it from this conversation,
   so it's safe to overwrite directly. Updated: Phase 11's installer status, the new
   `llm_model` gap flagged in both the source-file table and Known Gaps section, and a
   new dated update at the bottom (older dated updates preserved, per the file's own
   append convention).

4. **`docs/PHASES_md_Phase11_replacement_block.md`** — **not a drop-in file.** Your real
   `PHASES.md` has 18 phases and I only need to change one of them — regenerating the
   whole file risked introducing a subtle diff in a section I don't need to touch. Open
   your real `docs/PHASES.md`, find the `## Phase 11 — Packaging & distribution` section,
   and replace just that block with this file's content.

5. **`docs/DECISIONS_new_entry.md`** — **not a drop-in file, and the ordering note in an
   earlier version of this README was wrong.** Your real `DECISIONS.md` is chronological
   **oldest-first** (2026-07-09 at the top, 2026-08-06 at the bottom) — so this entry goes
   at the very **END** of the file, right after the existing 2026-08-06 entry, not at the
   top. See `docs/DECISIONS_APPEND_NOTE.md` for the same correction in one place.

6. **`docs/DECISIONS_APPEND_NOTE.md`** — short correction note, see above.

7. **`PATCH_config_and_env_example.md`** — two one-line manual edits for
   `src/config.py` and `.env.example`, fixing the dead `gemini-2.5-flash` default at
   the source. Not regenerated as full files since I only ever saw grep'd lines from
   each, not their complete contents.

## Suggested order of operations

1. Copy `installer/pixel-agent.iss`, `docs/RELEASE.md`, and `docs/STATUS.md` into your
   real project, overwriting the existing copies.
2. Open your real `docs/PHASES.md` and replace its Phase 11 section with
   `docs/PHASES_md_Phase11_replacement_block.md`'s content.
3. Append `docs/DECISIONS_new_entry.md`'s content to the END of your real
   `docs/DECISIONS.md`.
4. Apply the two one-line edits from `PATCH_config_and_env_example.md`.
5. Rebuild: `pyinstaller --name pixel-gui ...` → `robocopy` staging →
   `ISCC.exe installer\pixel-agent.iss`.
6. Fresh install, confirm a browser task works with zero manual `.env` patching this
   time — the real proof tonight's fix is baked into the build, not just patched on one
   machine.
