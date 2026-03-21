"""
src/organisms/cell.py

Cell — a differentiated StemCell that has committed to a specific role.

A Cell extends StemCell with:
  - A confirmed AgentRole (set at differentiation)
  - Role-specific behaviour during the step loop
  - A specialisation score that increases with focused activity
  - The ability to emit typed signals to the slime mold network
  - A clustering drive — cells seek other cells of similar/complementary roles

When enough Cells with compatible functions cluster (via the slime mold
network), they form an Organ.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.core.genome import Genome
from src.core.stem_cell import StemCell
from src.mouseion.contracts import AgentRole, EventEnvelopeV0, EventKind, ResourceKind
from src.slime_mold.signal import Signal, SignalType
from src.utils.helpers import clamp, get_logger, new_id

if TYPE_CHECKING:
    from src.core.environment import Environment
    from src.slime_mold.network import SlimeMoldNetwork

logger = get_logger("cell")

# Role compatibility map — which roles work well together in an organ
COMPATIBLE_ROLES: dict[AgentRole, list[AgentRole]] = {
    AgentRole.RESEARCHER: [AgentRole.SYNTHESIZER, AgentRole.CURATOR, AgentRole.CODER],
    AgentRole.CODER: [AgentRole.CRITIC, AgentRole.RESEARCHER, AgentRole.INNOVATOR],
    AgentRole.CRITIC: [AgentRole.CODER, AgentRole.RESEARCHER, AgentRole.GUARDIAN],
    AgentRole.SYNTHESIZER: [AgentRole.RESEARCHER, AgentRole.CONNECTOR, AgentRole.CURATOR],
    AgentRole.CURATOR: [AgentRole.RESEARCHER, AgentRole.SYNTHESIZER, AgentRole.GUARDIAN],
    AgentRole.CONNECTOR: [AgentRole.SYNTHESIZER, AgentRole.INNOVATOR, AgentRole.RESEARCHER],
    AgentRole.INNOVATOR: [AgentRole.CODER, AgentRole.CONNECTOR, AgentRole.RESEARCHER],
    AgentRole.GUARDIAN: [AgentRole.CRITIC, AgentRole.CURATOR, AgentRole.CONNECTOR],
}


class Cell(StemCell):
    """
    A differentiated, role-committed agent.

    Cells are more energy-efficient than StemCells in their area of
    specialisation but are less flexible — they cannot easily change roles
    once committed.

    Parameters
    ----------
    role:
        The confirmed role this cell plays.
    genome, initial_energy, parent_id, rng:
        Inherited from StemCell.
    """

    def __init__(
        self,
        role: AgentRole,
        genome: Genome | None = None,
        initial_energy: float = 10.0,
        parent_id: str | None = None,
        rng: random.Random | None = None,
    ) -> None:
        super().__init__(genome=genome, initial_energy=initial_energy,
                         parent_id=parent_id, rng=rng)
        self.agent_id = new_id("cell_")
        self.role = role
        self._differentiated = True
        self.specialisation_score: float = 0.1   # grows with focused activity
        self._organ_id: str | None = None         # set when joined an organ
        self._network: "SlimeMoldNetwork | None" = None

    # ------------------------------------------------------------------
    # Network attachment
    # ------------------------------------------------------------------

    def attach_to_network(self, network: "SlimeMoldNetwork") -> None:
        self._network = network
        network.add_agent(self.agent_id, role=self.role.value)
        network.subscribe(self.agent_id, self._on_signal_received)

    # ------------------------------------------------------------------
    # Differentiated step loop
    # ------------------------------------------------------------------

    def step(self, env: "Environment") -> None:
        """Role-specific behaviour each tick."""
        self._draw_resources(env)
        self._perform_role_action(env)
        self._seek_cluster_partners(env)
        self._age()

    def _draw_resources(self, env: "Environment") -> None:
        """Differentiated cells draw resources more efficiently."""
        efficiency = 1.0 + self.specialisation_score * 0.5 + self.genome.specialisation * 0.3
        drawn = env.mouseion.draw_resource(
            ResourceKind.ENERGY, 2.0 * efficiency, self.agent_id
        )
        self.energy += drawn

    def _perform_role_action(self, env: "Environment") -> None:
        """Execute role-specific behaviour."""
        if self.role == AgentRole.RESEARCHER:
            self._research_action(env)
        elif self.role == AgentRole.CODER:
            self._code_action(env)
        elif self.role == AgentRole.CRITIC:
            self._critic_action(env)
        elif self.role == AgentRole.SYNTHESIZER:
            self._synthesize_action(env)
        elif self.role == AgentRole.CURATOR:
            self._curate_action(env)
        elif self.role == AgentRole.CONNECTOR:
            self._connect_action(env)
        elif self.role == AgentRole.INNOVATOR:
            self._innovate_action(env)
        elif self.role == AgentRole.GUARDIAN:
            self._guard_action(env)

        # All roles increase specialisation over time
        self.specialisation_score = clamp(
            self.specialisation_score + 0.01 * self.genome.persistence
        )

    def _research_action(self, env: "Environment") -> None:
        if self.rng.random() < 0.3 * self.genome.curiosity:
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=f"Research finding at tick {env.tick_count} by {self.agent_id}",
                topic_tags=["research", self.role.value],
                confidence=clamp(0.4 + self.specialisation_score * 0.5),
            )
            if self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.KNOWLEDGE,
                    source_id=self.agent_id,
                    strength=0.7,
                    payload={"record_id": record.record_id},
                ), self.agent_id)

    def _code_action(self, env: "Environment") -> None:
        if self.rng.random() < 0.2 * self.genome.persistence:
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=f"Code artifact at tick {env.tick_count}",
                topic_tags=["code", "implementation"],
                confidence=clamp(0.5 + self.specialisation_score * 0.4),
            )

    def _critic_action(self, env: "Environment") -> None:
        # Critics evaluate existing knowledge
        records = list(env.mouseion.all_knowledge())
        if records and self.rng.random() < 0.25:
            target = self.rng.choice(records)
            updated_confidence = clamp(target.confidence - 0.05 + self.genome.compassion * 0.1)
            # In a full implementation: update the record's confidence with proper evaluation
            if self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.SYNC,
                    source_id=self.agent_id,
                    strength=0.5,
                    payload={"critique_of": target.record_id},
                ), self.agent_id)

    def _synthesize_action(self, env: "Environment") -> None:
        # Synthesizers combine knowledge from multiple records
        tags = ["research", "code", "innovation"]
        combined = []
        for tag in tags:
            combined.extend(env.mouseion.query_knowledge(tag)[:2])
        if len(combined) >= 2 and self.rng.random() < 0.2:
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=f"Synthesis at tick {env.tick_count} combining {len(combined)} sources",
                topic_tags=["synthesis", "meta"],
                confidence=clamp(0.6 + self.specialisation_score * 0.3),
                provenance_refs=[r.record_id for r in combined],
            )

    def _curate_action(self, env: "Environment") -> None:
        # Curators maintain knowledge quality (placeholder for full impl)
        pass

    def _connect_action(self, env: "Environment") -> None:
        # Connectors broadcast food/opportunity signals to the network
        if self._network and self.rng.random() < 0.4:
            self._network.broadcast(Signal(
                signal_id=new_id("sig_"),
                signal_type=SignalType.OPPORTUNITY,
                source_id=self.agent_id,
                strength=0.6 * self.genome.cooperation,
                payload={"role": self.role.value},
            ), self.agent_id)

    def _innovate_action(self, env: "Environment") -> None:
        if self.rng.random() < 0.15 * self.genome.creativity:
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=f"Novel approach proposed at tick {env.tick_count}",
                topic_tags=["innovation", "novel"],
                confidence=clamp(0.3 + self.genome.creativity * 0.5),
            )

    def _guard_action(self, env: "Environment") -> None:
        # Guardians monitor for low-energy agents and broadcast danger signals
        agents = env.all_agents()
        low_energy = [a for a in agents if a.energy < 3.0]
        if low_energy and self._network:
            self._network.broadcast(Signal(
                signal_id=new_id("sig_"),
                signal_type=SignalType.DANGER,
                source_id=self.agent_id,
                strength=0.8,
                payload={"low_energy_agents": [a.agent_id for a in low_energy[:5]]},
            ), self.agent_id)

    def _seek_cluster_partners(self, env: "Environment") -> None:
        """Connect to compatible nearby cells in the slime mold network."""
        if self._network is None:
            return
        signals = env.proximity_signals(self.agent_id)
        compat = COMPATIBLE_ROLES.get(self.role, [])
        for sig in signals:
            if sig.role in compat:
                self._network.connect(self.agent_id, sig.agent_id)
                self._network.reinforce(self.agent_id, sig.agent_id)

    def _on_signal_received(self, signal: Signal) -> None:
        """React to incoming signals from the slime mold network."""
        if signal.signal_type == SignalType.FOOD:
            self.energy += signal.strength * 0.5
        elif signal.signal_type == SignalType.DANGER:
            # Move away (random repositioning in environment)
            pass  # Environment handles actual movement

    # ------------------------------------------------------------------
    # Organ membership
    # ------------------------------------------------------------------

    @property
    def organ_id(self) -> str | None:
        return self._organ_id

    def join_organ(self, organ_id: str) -> None:
        self._organ_id = organ_id
        logger.debug("Cell %s joined organ %s", self.agent_id, organ_id)

    def leave_organ(self) -> None:
        self._organ_id = None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        base = super().snapshot()
        base.update({
            "specialisation_score": round(self.specialisation_score, 3),
            "organ_id": self._organ_id,
            "compatible_roles": [r.value for r in COMPATIBLE_ROLES.get(self.role, [])],
        })
        return base

    def __repr__(self) -> str:
        return (
            f"Cell(id={self.agent_id}, role={self.role.value}, "
            f"energy={self.energy:.1f}, spec={self.specialisation_score:.2f})"
        )
