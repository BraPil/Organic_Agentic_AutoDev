"""
src/core/stem_cell.py

StemCell — the atomic, totipotent agent.

A StemCell is a blank slate.  It has:
  - A Genome (behavioral tendencies)
  - Energy (its current resource level)
  - A drive loop (seek resources → seek opportunities → seek niches → respond to proximity)
  - A differentiation pathway (when niche signal + energy threshold met → become a Cell)

StemCells do NOT have a fixed role.  Their role emerges from the environment.

Lifecycle:
    StemCell.step(env)
        → _seek_resources(env)       — draw energy from pools
        → _scan_proximity(env)       — observe neighbours
        → _evaluate_opportunities(env) — identify tasks or niches
        → _attempt_differentiation(env) — commit to a niche if threshold met
        → _age()                     — consume baseline energy
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.mouseion.contracts import AgentRole, EventEnvelopeV0, EventKind, ResourceKind
from organic_agentic_autodev.utils.helpers import clamp, get_logger, new_id, now_ms

if TYPE_CHECKING:
    from organic_agentic_autodev.core.environment import Environment

logger = get_logger("stem_cell")

# Energy cost of living per tick
BASELINE_ENERGY_COST = 0.5
# Energy drawn from the pool each tick when seeking resources
RESOURCE_DRAW_AMOUNT = 2.0
# Minimum energy to avoid immediate death
MIN_VIABLE_ENERGY = 0.1


@dataclass
class DifferentiationSignal:
    """Accumulated evidence pushing the stem cell toward a specific role."""
    role: AgentRole
    strength: float = 0.0   # [0, 1] — how strong the signal is
    ticks_active: int = 0

    def strengthen(self, delta: float) -> None:
        self.strength = clamp(self.strength + delta)
        self.ticks_active += 1

    def decay(self, rate: float = 0.05) -> None:
        self.strength = max(0.0, self.strength - rate)


class StemCell:
    """
    Totipotent atomic agent — the fundamental unit of the organic system.

    Parameters
    ----------
    genome:
        Behavioral blueprint.  If None, a blank-slate Genome is used.
    initial_energy:
        Starting energy.  Default 10.0.
    parent_id:
        ID of the parent agent (if spawned from another agent).
    rng:
        Seeded random instance for reproducibility.
    """

    def __init__(
        self,
        genome: Genome | None = None,
        initial_energy: float = 10.0,
        parent_id: str | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.agent_id: str = new_id("sc_")
        self.genome: Genome = genome or Genome.blank_slate()
        self.energy: float = initial_energy
        self.parent_id: str | None = parent_id
        self.rng: random.Random = rng or random.Random()
        self.role: AgentRole = AgentRole.STEM_CELL
        self.generation: int = 0
        self.age_ticks: int = 0

        # Differentiation signals — accumulated per role
        self._diff_signals: dict[AgentRole, DifferentiationSignal] = {}
        self._differentiated: bool = False

        # Memory: what the agent has observed this session
        self._observations: list[str] = []
        # Tasks the agent is actively pursuing
        self._active_tasks: list[str] = []

        logger.debug("StemCell %s created (energy=%.1f)", self.agent_id, self.energy)

    # ------------------------------------------------------------------
    # Drive loop — called by Environment.tick()
    # ------------------------------------------------------------------

    def step(self, env: "Environment") -> None:
        """Execute one simulation step."""
        if self._differentiated:
            self._differentiated_step(env)
            return

        self._seek_resources(env)
        self._scan_proximity(env)
        self._evaluate_opportunities(env)
        self._attempt_differentiation(env)
        self._decay_signals()
        self._age()

    def _seek_resources(self, env: "Environment") -> None:
        """Draw energy from the environment's resource pools."""
        drawn = env.mouseion.draw_resource(
            ResourceKind.ENERGY,
            RESOURCE_DRAW_AMOUNT * self.genome.curiosity,
            self.agent_id,
        )
        self.energy += drawn

        # High-curiosity agents also seek knowledge
        if self.genome.curiosity > 0.6:
            env.mouseion.draw_resource(ResourceKind.DATA, 0.5, self.agent_id)

    def _scan_proximity(self, env: "Environment") -> None:
        """
        Observe neighbours via proximity signals.
        Accumulate differentiation signal based on what niches are occupied
        nearby — stem cells tend to fill gaps, not duplicate existing roles.
        """
        signals = env.proximity_signals(self.agent_id)
        occupied_roles: dict[AgentRole, int] = {}
        for sig in signals:
            occupied_roles[sig.role] = occupied_roles.get(sig.role, 0) + 1

        # Record what we see
        if signals:
            obs = f"tick={env.tick_count}: {len(signals)} neighbours; roles={list(occupied_roles.keys())}"
            self._observations.append(obs)

        # Agents with high cooperation signal strengthen toward CONNECTOR role
        # when many diverse roles are present but no connector exists
        if AgentRole.CONNECTOR not in occupied_roles and len(occupied_roles) > 2:
            if self.genome.cooperation > 0.6:
                self._accumulate_diff_signal(AgentRole.CONNECTOR, 0.05)

    def _evaluate_opportunities(self, env: "Environment") -> None:
        """
        Evaluate open niches in the ecosystem and accumulate differentiation
        signal for roles where the genome fits well and urgency is high.
        """
        best = env.best_niche_for(self)
        if best is None:
            return

        affinity = best.genome_affinity(self.genome)
        signal_strength = affinity * best.urgency * 0.15

        # Risk-tolerant agents respond to more signals (broader scan)
        if self.genome.risk_tolerance > 0.5:
            for niche in env.open_niches()[:3]:
                self._accumulate_diff_signal(
                    niche.role,
                    niche.genome_affinity(self.genome) * niche.urgency * 0.08,
                )
        else:
            self._accumulate_diff_signal(best.role, signal_strength)

    def _attempt_differentiation(self, env: "Environment") -> None:
        """
        Commit to a niche if:
          1. The strongest differentiation signal exceeds the genome threshold
          2. The agent has enough energy to survive the transition
          3. An open niche of the target role exists
        """
        if not self._diff_signals:
            return

        # Find strongest signal
        strongest_role = max(self._diff_signals, key=lambda r: self._diff_signals[r].strength)
        sig = self._diff_signals[strongest_role]

        if (
            sig.strength >= self.genome.differentiation_threshold
            and self.energy >= self.genome.differentiation_min_energy * 20
        ):
            # Look for any open niche matching the strongest-signal role
            matching = [n for n in env.open_niches() if n.role == strongest_role]
            if matching:
                target = max(matching, key=lambda n: n.urgency)
                self._differentiate(strongest_role, target.niche_id, env)

    def _differentiate(self, role: AgentRole, niche_id: str, env: "Environment") -> None:
        """Commit to a role — the stem cell becomes a differentiated Cell."""
        reward = env.fill_niche(niche_id, self.agent_id)
        for kind, amount in reward.items():
            self.energy += amount if kind == ResourceKind.ENERGY else 0

        old_role = self.role
        self.role = role
        self._differentiated = True

        env.mouseion.emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.DIFFERENTIATION_COMPLETED,
            source_agent_id=self.agent_id,
            payload={
                "old_role": old_role.value,
                "new_role": role.value,
                "niche_id": niche_id,
                "energy_after": self.energy,
                "age_at_differentiation": self.age_ticks,
            },
        ))
        logger.info(
            "StemCell %s differentiated → %s (energy=%.1f, age=%d)",
            self.agent_id, role.value, self.energy, self.age_ticks,
        )

    def _differentiated_step(self, env: "Environment") -> None:
        """Behaviour after differentiation — role-specific actions."""
        # Draw resources based on role efficiency (specialised cells are more efficient)
        efficiency = 1.0 + self.genome.specialisation * 0.5
        drawn = env.mouseion.draw_resource(
            ResourceKind.ENERGY,
            RESOURCE_DRAW_AMOUNT * efficiency,
            self.agent_id,
        )
        self.energy += drawn

        # Contribute knowledge based on role
        if self.role == AgentRole.RESEARCHER and self.rng.random() < 0.3:
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=f"Observation at tick {env.tick_count}: research finding from agent {self.agent_id}",
                topic_tags=[self.role.value, "research"],
                confidence=clamp(self.genome.persistence * 0.8),
            )

        self._age()

    def _age(self) -> None:
        """Consume baseline energy; increase age."""
        cost = BASELINE_ENERGY_COST * (1.0 - self.genome.resilience * 0.3)
        self.energy = max(0.0, self.energy - cost)
        self.age_ticks += 1

    def _decay_signals(self) -> None:
        for sig in self._diff_signals.values():
            sig.decay(rate=0.03 * (1.0 - self.genome.persistence))

    def _accumulate_diff_signal(self, role: AgentRole, delta: float) -> None:
        if role not in self._diff_signals:
            self._diff_signals[role] = DifferentiationSignal(role=role)
        self._diff_signals[role].strengthen(delta)

    # ------------------------------------------------------------------
    # Proximity signal helpers — called by Environment
    # ------------------------------------------------------------------

    def current_seeking(self) -> list[str]:
        """What this agent is actively looking for (for proximity broadcast)."""
        seeking = []
        if self.energy < 5.0:
            seeking.append("energy")
        if not self._diff_signals:
            seeking.append("niche_signal")
        if self.genome.curiosity > 0.7:
            seeking.append("knowledge")
        return seeking

    def current_offering(self) -> list[str]:
        """What this agent can provide to neighbours."""
        offering = []
        if self.energy > 15.0:
            offering.append("energy")
        if self._differentiated:
            offering.append(self.role.value)
        if self.genome.cooperation > 0.7:
            offering.append("cooperation")
        return offering

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def is_differentiated(self) -> bool:
        return self._differentiated

    @property
    def strongest_signal(self) -> tuple[AgentRole, float] | None:
        if not self._diff_signals:
            return None
        role = max(self._diff_signals, key=lambda r: self._diff_signals[r].strength)
        return (role, self._diff_signals[role].strength)

    def snapshot(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "energy": round(self.energy, 2),
            "age_ticks": self.age_ticks,
            "differentiated": self._differentiated,
            "genome": self.genome.to_dict(),
            "strongest_signal": (
                {"role": s[0].value, "strength": round(s[1], 3)}
                if (s := self.strongest_signal) else None
            ),
            "observations": len(self._observations),
        }

    def __repr__(self) -> str:
        return (
            f"StemCell(id={self.agent_id}, role={self.role.value}, "
            f"energy={self.energy:.1f}, age={self.age_ticks})"
        )
