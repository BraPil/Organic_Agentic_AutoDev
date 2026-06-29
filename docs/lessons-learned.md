# Lessons Learned

Mistakes, surprises, and the preventive lesson each one taught. Unlike the discovery log (neutral
findings), entries here are *corrective* — something went wrong or nearly did, and here's how to
avoid it next time.

Format: `### YYYY-MM-DD — <title>` · **What happened** · **Lesson**.

---

### 2026-06-28 — A package named `src` collides with consumers that embed you

**What happened:** OAA originally exposed a top-level `src` package. When AAA embedded OAA as its P6
learning engine, AAA's own `src/` collided with it, breaking imports.

**Lesson:** A library meant to be embedded must use a unique, descriptive top-level package name
(`organic_agentic_autodev`). Never ship a generic `src` package for anything a consumer imports.

---

### 2026-06-28 — "It runs locally" can hide a missing declared dependency

**What happened:** Dashboard tests passed locally because `httpx` happened to be installed, but a
clean CI install would have errored — `httpx` is only an *optional* starlette dependency.

**Lesson:** A green local run is not proof of a reproducible build. Anything a test imports must be a
declared dependency in `pyproject`. Treat the clean-environment CI run as the source of truth.

---

### 2026-06-29 — A configured CLAUDE.md beats memory for cross-session continuity

**What happened:** Project state lived in agent memory files. Useful, but invisible to other
contributors and not enforced by any protocol. The standard CLAUDE.md template arrived unconfigured.

**Lesson:** Durable, in-repo tracking (CLAUDE.md + companion docs: decision/discovery/lessons logs)
is the canonical record. Agent memory is a convenience cache, not the system of record. Configure the
governance file early so "where we are" is committed, not remembered.
</content>
