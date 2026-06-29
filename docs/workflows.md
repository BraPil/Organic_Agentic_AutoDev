# Workflows

Development lifecycle, branching, commit standards, and PR process.

## Branching

- `main` is protected — never push directly (CLAUDE.md §3). Human gate required.
- One branch per feature/phase-task: `feature/<short-name>` (e.g. `feature/knowledge-wiki-ingest`).
- Merge back via `--no-ff` PR after review; delete the branch on merge.
- Phase 0 used the per-feature-branch model (`feature/llm-cognition` → … → `feature/distributed-ecosystem`),
  each merged `--no-ff` then deleted. Continue this pattern for Phase 1+.

## Session start (every session)

Follow CLAUDE.md §4: orient (`git status && git log --oneline -5`) → confirm baseline green
(`pytest tests/ -v`) → read relevant companion docs → check decision/discovery logs.

## Test command

```bash
pytest tests/ -v          # full suite (251 tests, ~2s, fully offline)
pytest tests/ -v -k NAME  # focused
```

`-v --tb=short` is already in `pyproject` `addopts`. CI installs `[dev,dashboard]` and runs on
py3.11 + py3.12. **Baseline must be green before any change; fix red first.**

## Commit standards

- Conventional-style prefixes: `feat`, `fix`, `refactor`, `docs`, `ci`, `test`, `chore`.
- The message body explains **why**, not just **what** (DoD requirement).
- Keep shell changes in their own commit, clearly labeled, with a decision-log entry.

## Definition of Done

See CLAUDE.md §5. A task is not done until code (tests offline-green, no new ruff warnings, no secrets,
sanitization in place), docs (companions + logs updated, ADR if a choice was locked), and hygiene
(no stray TODOs/dead code, why-explaining commit message) boxes are all checked.

## Adding a dependency

1. Justify it in CLAUDE.md §7 (Technology Stack table).
2. Add a `docs/decision-log.md` entry.
3. Prefer an optional extra (`[llm]`/`[vector]`/`[dashboard]`/`[distributed]`) over a core dep — core
   must stay offline-runnable.
4. Get owner approval (it's a **Block** action).
</content>
