"""
src/core/environment.py

The Environment — the living ecosystem that StemCell agents inhabit.

The Environment is responsible for:
  - Maintaining and slowly regenerating resource pools
  - Broadcasting proximity signals (what neighbours are doing)
  - Publishing open niches (what the ecosystem needs)
  - Advancing the simulation clock (ticks)
  - Registering and removing agents
  - Computing local neighbourhood for each agent (proximity-based signalling)

The Environment mediates between the Mouseion substrate (shared knowledge)
and the living agents — it is the air and soil in which cells grow.
"""

from __future__ import annotations

import math
import random
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.niche import Niche
from src.mouseion.contracts import (
    AgentRole,
    EventEnvelopeV0,
    EventKind,
    NicheAdvertisementV0,
    ResourceKind,
)
from src.mouseion.substrate import Mouseion
from src.utils.helpers import get_logger, new_id

if TYPE_CHECKING:
    from src.core.stem_cell import StemCell

logger = get_logger("environment")


@dataclass
class ProximitySignal:
    """What a neighbouring agent is broadcasting about its current state."""
    agent_id: str
    role: AgentRole
    energy: float
    dominant_trait: str
    seeking: list[str]     # what the agent is actively looking for
    offering: list[str]    # what the agent can share


class Environment:
    """
    The living ecosystem container.

    Simulation loop:
        env.tick()  — advance by one step
          → regenerate resources
          → age all niches
          → broadcast proximity signals
          → apply survival pressure (agents with too little energy die)
    """

    def __init__(
        self,
        mouseion: Mouseion,
        neighbourhood_radius: int = 5,
        resource_regen_rate: float = 0.02,
        rng: random.Random | None = None,
    ) -> None:
        self.mouseion = mouseion
        self.neighbourhood_radius = neighbourhood_radius
        self.resource_regen_rate = resource_regen_rate
        self.rng = rng or random.Random()
        self._tick_count = 0

        # Registered agents: id → StemCell (or subclass)
        self._agents: dict[str, "StemCell"] = {}
        # Spatial positions for proximity computation (simple 2-D grid)
        self._positions: dict[str, tuple[float, float]] = {}
        self._agent_lock = threading.Lock()

        # Niches managed by the environment
        self._niches: dict[str, Niche] = {}
        self._niche_lock = threading.Lock()

        # Proximity signal cache (rebuilt each tick)
        self._proximity_cache: dict[str, list[ProximitySignal]] = defaultdict(list)

        logger.info("Environment initialised (neighbourhood_radius=%d)", neighbourhood_radius)

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register(self, agent: "StemCell") -> None:
        """Add an agent to the ecosystem at a random position."""
        with self._agent_lock:
            self._agents[agent.agent_id] = agent
            self._positions[agent.agent_id] = (
                self.rng.uniform(0, 100),
                self.rng.uniform(0, 100),
            )
        logger.debug("Agent %s registered in environment", agent.agent_id)

    def deregister(self, agent_id: str) -> None:
        with self._agent_lock:
            self._agents.pop(agent_id, None)
            self._positions.pop(agent_id, None)

    def agent_count(self) -> int:
        with self._agent_lock:
            return len(self._agents)

    def all_agents(self) -> list["StemCell"]:
        with self._agent_lock:
            return list(self._agents.values())

    # ------------------------------------------------------------------
    # Niche management
    # ------------------------------------------------------------------

    def seed_niches(self, niches: list[Niche]) -> None:
        """Populate the ecosystem with initial niches."""
        with self._niche_lock:
            for niche in niches:
                self._niches[niche.niche_id] = niche
                self.mouseion.post_niche(NicheAdvertisementV0(
                    niche_id=niche.niche_id,
                    description=niche.description,
                    required_capabilities=[niche.role.value],
                    resource_reward=niche.base_reward,
                    urgency=niche.urgency,
                    posted_by="environment",
                ))
        logger.info("Seeded %d niches into environment", len(niches))

    def open_niches(self) -> list[Niche]:
        with self._niche_lock:
            return [n for n in self._niches.values() if n.is_open]

    def best_niche_for(self, agent: "StemCell") -> Niche | None:
        """Return the most urgent niche that best matches the agent's Genome."""
        open_n = self.open_niches()
        if not open_n:
            return None
        scored = [
            (n.urgency * n.genome_affinity(agent.genome), n)
            for n in open_n
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None

    def fill_niche(self, niche_id: str, agent_id: str) -> dict[ResourceKind, float]:
        """Mark a niche as filled; return the resource reward."""
        with self._niche_lock:
            niche = self._niches.get(niche_id)
            if niche is None or not niche.is_open:
                return {}
            niche.filled_by = agent_id
            reward = niche.effective_reward()
        self.mouseion.fill_niche(niche_id, agent_id)
        return reward

    # ------------------------------------------------------------------
    # Proximity signals
    # ------------------------------------------------------------------

    def proximity_signals(self, agent_id: str) -> list[ProximitySignal]:
        """Return cached proximity signals for the given agent."""
        return list(self._proximity_cache.get(agent_id, []))

    def _rebuild_proximity_cache(self) -> None:
        """Rebuild the proximity signal cache based on current positions."""
        with self._agent_lock:
            agents = list(self._agents.values())
            positions = dict(self._positions)

        new_cache: dict[str, list[ProximitySignal]] = defaultdict(list)
        for agent in agents:
            pos = positions.get(agent.agent_id, (0.0, 0.0))
            for other in agents:
                if other.agent_id == agent.agent_id:
                    continue
                other_pos = positions.get(other.agent_id, (0.0, 0.0))
                dist = math.sqrt((pos[0] - other_pos[0])**2 + (pos[1] - other_pos[1])**2)
                if dist <= self.neighbourhood_radius:
                    signal = ProximitySignal(
                        agent_id=other.agent_id,
                        role=other.role,
                        energy=other.energy,
                        dominant_trait=other.genome.dominant_trait(),
                        seeking=other.current_seeking(),
                        offering=other.current_offering(),
                    )
                    new_cache[agent.agent_id].append(signal)

        self._proximity_cache = new_cache

    def move_agent(self, agent_id: str, dx: float, dy: float) -> None:
        """Move an agent by (dx, dy), clamped to [0, 100]²."""
        with self._agent_lock:
            x, y = self._positions.get(agent_id, (50.0, 50.0))
            self._positions[agent_id] = (
                max(0.0, min(100.0, x + dx)),
                max(0.0, min(100.0, y + dy)),
            )

    # ------------------------------------------------------------------
    # Simulation tick
    # ------------------------------------------------------------------

    def tick(self) -> dict:
        """Advance the simulation by one step. Returns a summary dict."""
        self._tick_count += 1

        # 1. Regenerate resources
        for pool in self.mouseion._pools.values():
            regen = pool._amount * self.resource_regen_rate
            pool.deposit(regen, agent_id="environment")

        # 2. Age all niches
        with self._niche_lock:
            for niche in self._niches.values():
                niche.tick()

        # 3. Rebuild proximity cache
        self._rebuild_proximity_cache()

        # 4. Let agents act (basic drive-based step)
        dead_agents: list[str] = []
        with self._agent_lock:
            agents = list(self._agents.values())
        for agent in agents:
            agent.step(self)
            if agent.energy <= 0:
                dead_agents.append(agent.agent_id)

        # 5. Remove dead agents
        for agent_id in dead_agents:
            self.deregister(agent_id)
            logger.info("Agent %s died (energy=0)", agent_id)

        return {
            "tick": self._tick_count,
            "agents_alive": self.agent_count(),
            "agents_died": len(dead_agents),
            "open_niches": len(self.open_niches()),
        }

    @property
    def tick_count(self) -> int:
        return self._tick_count

    # ------------------------------------------------------------------
    # Factory: default niche set
    # ------------------------------------------------------------------

    @staticmethod
    def default_niche_set() -> list[Niche]:
        """Create a representative starter set of niches for a new ecosystem."""
        niches = []
        role_descriptions = {
            AgentRole.RESEARCHER: "Explore and synthesize new knowledge from the Mouseion",
            AgentRole.CODER: "Implement and test solutions to active problems",
            AgentRole.CRITIC: "Evaluate outputs and surface weaknesses",
            AgentRole.SYNTHESIZER: "Integrate findings across agents into coherent narratives",
            AgentRole.CURATOR: "Maintain knowledge record quality and provenance",
            AgentRole.CONNECTOR: "Build bridges between isolated agent clusters",
            AgentRole.INNOVATOR: "Propose and prototype novel approaches",
            AgentRole.GUARDIAN: "Protect system health and prevent harmful outputs",
        }
        for i, (role, desc) in enumerate(role_descriptions.items()):
            niches.append(Niche(
                niche_id=new_id("niche_"),
                role=role,
                description=desc,
                urgency=0.3 + (i % 3) * 0.1,
                base_reward={
                    ResourceKind.ENERGY: 5.0,
                    ResourceKind.KNOWLEDGE: 3.0,
                    ResourceKind.TRUST: 2.0,
                },
                urgency_growth_rate=0.015 + i * 0.002,
            ))
        return niches
