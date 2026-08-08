# Two small follow-up edits, NOT included as full files in this zip

I only have partial contents of `src/config.py` and `.env.example` from this
conversation (a few grep'd lines each), not the complete files — so rather than
regenerate them from scratch and risk silently dropping something real, here are the
exact, minimal edits to make by hand. Both are one-line changes.

## 1. `src/config.py`, line 168

Find:
```python
llm_model=os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
```

Replace with:
```python
llm_model=os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite"),
```

This is the same change you already made by hand-editing the installed `.env` — this
edit makes it the actual default for every *future* install, so the next person (or your
next clean reinstall) doesn't hit the same dead-model 404 on their very first task.

## 2. `.env.example`, line 4

Find:
```
LLM_MODEL=gemini-2.5-flash
```

Replace with:
```
LLM_MODEL=gemini-3.5-flash-lite
```

## Why these weren't rebuilt as full files

`config.py` in particular is a large, heavily cross-referenced file (risk model
backends, execution mode, rate-limit settings, encryption config, and more per
`docs/DECISIONS.md`'s history) — regenerating it from a handful of grep'd lines risks
me confidently reconstructing something that looks right but silently drops or
misorders a real field. A one-line `str_replace` on your actual file is safer than a
from-scratch rewrite here.

## After making both edits

- Re-run your test suite (`docs/STATUS.md` says 395 tests should pass, GUI included, in
  an environment with PySide6 installed) to confirm nothing else references
  `"gemini-2.5-flash"` as a hardcoded string (e.g. a stale assertion in
  `tests/test_config.py`) that would now fail against the new default.
- Rebuild PyInstaller + recompile the installer if you want this baked into your next
  release `.exe` — the workaround you applied tonight only patched the one already-
  installed copy on this machine.
