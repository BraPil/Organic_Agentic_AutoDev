"""
src/slime_mold/signal.py

Chemical-analog signal propagation for the slime mold network.

Physarum polycephalum communicates through chemical gradients — tubes that
carry material contract and expand based on flux, strengthening high-flow
paths and allowing low-flow paths to atrophy.

We model this with a discrete signal propagation system:
  - Signals are emitted at source nodes with a given strength
  - Each tick, signals propagate along edges, attenuating with distance
  - Nodes accumulate signal and re-emit to neighbours at reduced strength
  - Edges that carry high-signal flux are reinforced; low-flux edges decay

Signal types correspond to resource/need broadcasts:
  FOOD        — resource availability
  DANGER      — threat or energy depletion
  OPPORTUNITY — an open niche or task
  KNOWLEDGE   — new information in the Mouseion
  SYNC        — coordination pulse from an Organ or Body
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SignalType(str, Enum):
    FOOD = "food"
    DANGER = "danger"
    OPPORTUNITY = "opportunity"
    KNOWLEDGE = "knowledge"
    SYNC = "sync"


@dataclass
class Signal:
    """A signal packet propagating through the slime mold network."""
    signal_id: str
    signal_type: SignalType
    source_id: str
    strength: float          # [0, 1] — attenuates as it propagates
    payload: dict = field(default_factory=dict)
    hops: int = 0
    max_hops: int = 6

    @property
    def is_alive(self) -> bool:
        return self.strength > 0.01 and self.hops < self.max_hops

    def attenuate(self, factor: float = 0.7) -> "Signal":
        """Return a weakened copy of this signal for the next hop."""
        return Signal(
            signal_id=self.signal_id,
            signal_type=self.signal_type,
            source_id=self.source_id,
            strength=self.strength * factor,
            payload=self.payload,
            hops=self.hops + 1,
            max_hops=self.max_hops,
        )

    def __repr__(self) -> str:
        return (
            f"Signal({self.signal_type.value}, src={self.source_id}, "
            f"strength={self.strength:.3f}, hops={self.hops})"
        )
