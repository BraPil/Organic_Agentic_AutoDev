"""
src/cognition/bridge.py

The cognition bridge: runs one role-based research cycle (Researcher → Critic →
Synthesizer) over a seeded question, grounded in caller-supplied context, and
emits KnowledgeRecordV0 artifacts into the Mouseion.

Pipeline:
    seed spec (question + agents + grounding)
        → researchers each produce a grounded finding
        → critics adversarially score the findings (EvaluationV0)
        → synthesizer composes a candidate artifact
        → confidence(synthesis) = mean(critic overall_scores)

The synthesizer's artifact is the high-value candidate AAA later reviews and
(if a human approves) promotes from `experimental` to `grounded`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

from src.mouseion.contracts import EvaluationV0, KnowledgeRecordV0
from src.mouseion.substrate import Mouseion
from src.utils.helpers import get_logger, new_id, sanitize_text

logger = get_logger("cognition.bridge")

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1024


# ---------------------------------------------------------------------------
# Shell contract
# ---------------------------------------------------------------------------

class CognitionProvider(Protocol):
    """Stable interface for a thinking backend (flesh is swappable)."""

    def generate(self, system: str, prompt: str) -> str:
        ...


# ---------------------------------------------------------------------------
# Flesh: Anthropic
# ---------------------------------------------------------------------------

class AnthropicCognition:
    """LLM cognition backed by the Anthropic API."""

    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        import anthropic  # noqa: PLC0415
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._model = model

    def generate(self, system: str, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()


# ---------------------------------------------------------------------------
# Flesh: deterministic fallback (no API key — keeps the pipeline runnable in CI)
# ---------------------------------------------------------------------------

class DeterministicCognition:
    """Offline fallback that echoes structured, grounded-looking output."""

    def generate(self, system: str, prompt: str) -> str:
        # Return valid JSON so the parsing path is exercised without an API key.
        return json.dumps({
            "finding": "[deterministic] no LLM available; grounding context echoed.",
            "confidence": 0.5,
            "score": 0.5,
            "critique": "[deterministic] no adversarial review performed.",
            "synthesis": "[deterministic] no synthesis performed.",
        })


def make_cognition(model: str = _DEFAULT_MODEL) -> CognitionProvider:
    """Return an Anthropic provider if a key is present, else the deterministic one."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicCognition(model=model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic cognition unavailable (%s) — using deterministic", exc)
    return DeterministicCognition()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from an LLM response."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to treating the whole text as the content.
        return {}


def _clamp01(x: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------

class LearningCycle:
    """Runs one Researcher → Critic → Synthesizer cycle and stores artifacts."""

    def __init__(self, cognition: CognitionProvider | None = None,
                 mouseion: Mouseion | None = None) -> None:
        self._cog = cognition or make_cognition()
        self._mouseion = mouseion or Mouseion()

    # -- role prompts -------------------------------------------------------

    def _research(self, persona: dict, question: str, grounding: str) -> dict:
        system = (
            f"You are {persona.get('display_name', persona['agent_id'])}, an AI architecture "
            "researcher. Produce a specific, defensible finding grounded ONLY in the provided "
            "evidence. Do not invent sources. Return JSON: "
            '{"finding": "...", "confidence": 0.0-1.0, "topics": ["..."]}'
        )
        prompt = f"QUESTION:\n{question}\n\nEVIDENCE:\n{grounding}\n\nReturn only JSON."
        data = _parse_json(self._cog.generate(system, prompt))
        return {
            "author_id": f"researcher_{persona['agent_id']}",
            "finding": data.get("finding", "").strip() or "(no finding)",
            "confidence": _clamp01(data.get("confidence"), 0.6),
            "topics": data.get("topics", []) if isinstance(data.get("topics"), list) else [],
        }

    def _critique(self, critic: dict, finding: str, question: str) -> dict:
        system = (
            f"You are {critic.get('display_name', critic['agent_id'])}, an adversarial critic. "
            "Score the finding for grounding, correctness, and relevance to the question. Be "
            'skeptical. Return JSON: {"score": 0.0-1.0, "critique": "one or two sentences"}'
        )
        prompt = f"QUESTION:\n{question}\n\nFINDING:\n{finding}\n\nReturn only JSON."
        data = _parse_json(self._cog.generate(system, prompt))
        return {
            "evaluator_id": f"critic_{critic['agent_id']}",
            "score": _clamp01(data.get("score"), 0.5),
            "critique": data.get("critique", "").strip(),
        }

    def _synthesise(self, synthesizer: dict, question: str,
                    findings: list[dict], critiques: list[dict]) -> str:
        findings_txt = "\n\n".join(f"- {f['finding']}" for f in findings)
        crit_txt = "\n".join(f"- ({c['score']:.2f}) {c['critique']}" for c in critiques)
        system = (
            f"You are {synthesizer.get('display_name', synthesizer['agent_id'])}, a synthesizer. "
            "Compose the reviewed findings into a single, actionable architecture recommendation. "
            "Prefer findings the critics rated highly. Be concrete and concise (3-5 sentences)."
        )
        prompt = (
            f"QUESTION:\n{question}\n\nFINDINGS:\n{findings_txt}\n\n"
            f"CRITIC NOTES:\n{crit_txt}\n\nReturn the recommendation as plain prose."
        )
        return self._cog.generate(system, prompt).strip()

    # -- orchestration ------------------------------------------------------

    def run(self, seed: dict) -> list[KnowledgeRecordV0]:
        """Run the cycle for a seed spec; returns all stored KnowledgeRecordV0."""
        question = seed.get("niche", {}).get("description", "").strip()
        grounding = seed.get("grounding", "").strip() or "(no external evidence supplied)"
        agents = seed.get("agents", [])
        if not question or not agents:
            raise ValueError("seed must include niche.description and at least one agent")

        researchers = [a for a in agents if a.get("suggested_role") == "researcher"] or agents[:1]
        critics = [a for a in agents if a.get("suggested_role") == "critic"] or agents
        synth = next((a for a in agents if a.get("suggested_role") == "synthesizer"), agents[-1])

        logger.info("Cycle: %d researchers, %d critics, synthesizer=%s",
                    len(researchers), len(critics), synth["agent_id"])

        # 1. Research (self-rated confidence is provisional — critics decide below)
        findings = [self._research(r, question, grounding) for r in researchers]

        # 2. Critique: every critic reviews every finding. A finding's stored
        # confidence is the MEAN critic score (adversarially earned), not the
        # researcher's self-rating — self-assessment must never drive the gate.
        all_evals: list[dict] = []
        finding_records: list[KnowledgeRecordV0] = []
        for f in findings:
            f_evals = [self._critique(c, f["finding"], question) for c in critics]
            all_evals.extend(f_evals)
            earned = sum(e["score"] for e in f_evals) / len(f_evals) if f_evals else f["confidence"]
            rec = self._mouseion.store_knowledge(
                author_id=f["author_id"], content=f["finding"],
                topic_tags=f["topics"], confidence=round(earned, 4),
            )
            finding_records.append(rec)

        # 3. Synthesise — confidence = mean critic score (adversarial consensus)
        synth_text = self._synthesise(synth, question, findings, all_evals)
        mean_score = sum(e["score"] for e in all_evals) / len(all_evals) if all_evals else 0.5
        review_history = [
            EvaluationV0(
                evaluation_id=new_id("ev_"),
                subject_id="synthesis",
                evaluator_id=e["evaluator_id"],
                criteria={"adversarial": e["score"]},
                overall_score=e["score"],
                notes=sanitize_text(e["critique"])[:300],
            )
            for e in all_evals
        ]
        synth_record = self._mouseion.store_knowledge(
            author_id=f"synthesizer_{synth['agent_id']}",
            content=synth_text,
            topic_tags=seed.get("niche", {}).get("required_capabilities", []),
            confidence=round(mean_score, 4),
            provenance_refs=[r.record_id for r in finding_records],
        )
        # Attach the adversarial review history to the synthesis record.
        synth_record.review_history.extend(review_history)

        logger.info("Cycle complete: %d findings, synthesis confidence %.3f",
                    len(finding_records), mean_score)
        return [*finding_records, synth_record]
