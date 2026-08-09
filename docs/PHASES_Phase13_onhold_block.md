# Replacement for docs/PHASES.md's Phase 13 section only

Find "## Phase 13 — Docker deployment (full desktop automation, via nested Windows VM)"
in your real PHASES.md and replace its status line / add this note directly under the
heading, before the existing "Goal:" paragraph. Keep the existing file table and
success criterion below it exactly as they are — nothing about the plan changed, only
its current priority.

---

## Phase 13 — Docker deployment (full desktop automation, via nested Windows VM)
**Status: ON HOLD (2026-08-09).** A first pass at this phase's files (Dockerfile,
provision.ps1, docker-compose.desktop.yml, reset-snapshot.sh, docs/DOCKER_DESKTOP.md)
was written on 2026-08-09 but deliberately not applied to this repo — see
`docs/DECISIONS.md`'s matching entry. Reason: this is the first phase in the project's
history that cannot be verified on the Windows machine used for every prior live-run
phase (7 through 12) — it requires a *separate* Linux host with `/dev/kvm` exposed,
infrastructure not confirmed available. Rather than build out a phase that can't be
tested, deliberately deferred until after Phase 14 (and, time permitting, 15-18) are
complete — revisit once either that hardware is available or the roadmap has otherwise
circled back with nothing else higher-priority left. The written-but-unapplied files
from the 2026-08-09 attempt remain available if/when this phase resumes; they weren't
discarded, just not merged into the working repo.

(existing "Goal:", file table, and success criterion continue unchanged below)
