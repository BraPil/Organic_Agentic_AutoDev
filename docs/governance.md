# Governance

Protected paths, file ownership, and approval escalation. This expands CLAUDE.md §3.

## Project owner

**Brandt Pileggi** — final approval authority, defines "done", holds veto.

## Protected paths (the MoltBook *shell*)

Changing any of these is a **shell change**: it can break downstream consumers (AAA, ExMorbus).
Requires explicit owner approval and a version bump. Prefer additive *flesh* instead.

| Path | Why protected |
|------|---------------|
| `organic_agentic_autodev/mouseion/contracts.py` | Pydantic V0 wire contracts + enums; the data shape consumers depend on |
| `organic_agentic_autodev/core/genome.py` | Genome trait set + defaults (compassion is first-class) |
| `organic_agentic_autodev/slime_mold/signal.py` | Signal types — chemical-analog message contract |
| `organic_agentic_autodev/observability/contracts.py` | SLI/SLO/SLA schemas |
| `organic_agentic_autodev/domain/exmorbus/contracts.py` | Medical knowledge contracts |
| `organic_agentic_autodev/cognition/bridge.py` (+ `run_cycle.py`) | `KnowledgeRecordV0` JSONL boundary — the OAA→consumer seam; confidence = mean critic score |
| All `__init__.py` public exports | The importable API surface |
| `.github/workflows/` | CI affects every contributor |
| `pyproject.toml` dependencies/extras | Security + bloat + consumer install footprint |

## Approval-gated actions

See CLAUDE.md §3 for the full table. Summary of **Block** (stop and get approval):
delete/overwrite outside task scope · change shell contracts · add dependencies · commit secrets ·
modify CI/CD · push to `main`/release · irreversible infra changes.

**Ask** (pause and confirm): refactor outside stated scope · cite an unverified API.

## Ownership discipline

Every task declares its **file scope** upfront. A file modified without being in the declared scope is
a governance smell — surface it rather than silently expanding the blast radius.

## The pristine-core rule

OAA core carries **no consumer-specific glue**. AAA-specific or ExMorbus-specific logic belongs in the
consumer repo. This is grep-verifiable and is a review gate, not a guideline.
</content>
