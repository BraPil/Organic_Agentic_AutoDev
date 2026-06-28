"""
src/cognition/contracts.py

Shell contracts for the LLM cognition layer.

These are stable, versioned Pydantic schemas (MoltBook shell). The flesh — the
actual LLM providers (Anthropic, OpenAI) and the MockProvider — depends on
these contracts, never the other way round.

A CognitionRequestV0 is what an agent "thinks about": its role, its genome
bias, the sanitised context drawn from the Mouseion, and the task at hand.

A CognitionResponseV0 is the structured result of that cognition. It is
produced via LLM tool-use / structured output so that only validated, typed
data ever enters the Mouseion knowledge store — never raw model text.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CognitiveAction(str, Enum):
    """What the agent decided to do after reasoning."""
    CONTRIBUTE_KNOWLEDGE = "contribute_knowledge"   # produce a new knowledge record
    SYNTHESISE = "synthesise"                       # combine existing records
    CRITIQUE = "critique"                           # flag a weakness in a record
    DEFER = "defer"                                 # nothing worth contributing this tick


class CognitionRequestV0(BaseModel):
    """
    A single cognition request — the prompt-shaping inputs for one LLM call.

    All free-text fields (``context`` especially) MUST already be sanitised by
    the caller via ``sanitize_text`` before construction. Providers re-sanitise
    defensively, but the contract is: nothing raw reaches the model.
    """
    role: str                                   # AgentRole value, e.g. "oncologist"
    genome_bias: str                            # qualitative trait instructions
    task: str                                   # what the ecosystem needs right now
    context: str = ""                           # sanitised Mouseion context
    available_tags: list[str] = Field(default_factory=list)
    tick: int = 0
    schema_version: str = "v0"


class CognitionResponseV0(BaseModel):
    """
    Structured output of one cognition call.

    Forced through LLM structured output / tool use so it is always valid —
    the ``content`` field is what gets stored (after sanitisation) as a
    KnowledgeRecordV0; ``confidence`` flows straight into the record.
    """
    action: CognitiveAction
    content: str = Field(description="The knowledge contribution, ≤ 600 chars")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Brief rationale, ≤ 300 chars")
    topic_tags: list[str] = Field(default_factory=list)
    schema_version: str = "v0"
