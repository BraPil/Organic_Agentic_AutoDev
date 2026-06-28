"""
src/dashboard/sim_runner.py

DashboardSimulation — a self-contained, observable ecosystem for the dashboard.

This is dependency-free (no FastAPI): it assembles a full ecosystem — Mouseion,
Environment, SlimeMoldNetwork, Body, SLITracker, and a colony of agents — and
exposes:

  - ``step()``      : advance the whole ecosystem one tick
  - ``snapshot()``  : a JSON-serialisable state dict for the UI
  - ``history()``   : compact time-series for charts

Because it is pure Python, the simulation and its state shaping are fully unit
tested offline; the FastAPI app (app.py) is a thin transport layer on top.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.core.stem_cell import StemCell
from organic_agentic_autodev.domain.exmorbus import create_medical_genome, create_medical_niches, seed_mouseion
from organic_agentic_autodev.mouseion.contracts import AgentRole, EventKind, ResourceKind
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.observability import SLITracker, build_medical_sla
from organic_agentic_autodev.organisms.body import Body
from organic_agentic_autodev.organisms.cell import Cell
from organic_agentic_autodev.organisms.organ import Organ
from organic_agentic_autodev.slime_mold.network import SlimeMoldNetwork
from organic_agentic_autodev.utils.helpers import get_logger

logger = get_logger("dashboard.sim")

_MEDICAL_ROLES = [
    AgentRole.ONCOLOGIST, AgentRole.PATHOLOGIST, AgentRole.CLINICAL_TRIALIST,
    AgentRole.GENETICIST, AgentRole.PHARMACOLOGIST, AgentRole.RADIOLOGIST,
    AgentRole.PATIENT_ADVOCATE, AgentRole.EPIDEMIOLOGIST,
]


class DashboardSimulation:
    """An observable medical-oncology ecosystem driving the live dashboard."""

    def __init__(self, n_stem_cells: int = 24, seed: int = 42,
                 initial_energy: float = 4000.0) -> None:
        self._rng = random.Random(seed)
        self._initial_energy = initial_energy

        self.mouseion = Mouseion(initial_resources={ResourceKind.ENERGY: initial_energy})
        self.env = Environment(mouseion=self.mouseion, neighbourhood_radius=20, rng=self._rng)
        seed_mouseion(self.mouseion)
        self.niches = create_medical_niches()
        self.env.seed_niches(self.niches)

        self.network = SlimeMoldNetwork(rng=self._rng)
        self.body = Body("ExMorbus Oncology Intelligence")
        self.body.attach_to_network(self.network)
        self.sla = build_medical_sla()
        self.tracker = SLITracker(mouseion=self.mouseion, environment=self.env,
                                  sla=self.sla, body=self.body,
                                  initial_energy=initial_energy)

        for i in range(n_stem_cells):
            role = _MEDICAL_ROLES[i % len(_MEDICAL_ROLES)]
            genome = create_medical_genome(role, rng=self._rng)
            cell = StemCell(genome=genome, initial_energy=25.0,
                            rng=random.Random(self._rng.randint(0, 99999)))
            self.env.register(cell)

        self.tick = 0
        self.organs: list[Organ] = []
        self._knowledge_series: deque[tuple[int, int]] = deque(maxlen=200)
        self._compliance_series: deque[tuple[int, float]] = deque(maxlen=200)
        self._last_cluster_tick = 0

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def step(self) -> dict[str, Any]:
        """Advance the ecosystem by one tick and return the new snapshot."""
        self.tick += 1
        self.env.tick()
        self.network.tick()
        report = self.tracker.tick()
        self.body.step(self.env)
        self._maybe_form_organ()

        self._knowledge_series.append((self.tick, self.mouseion.knowledge_count()))
        self._compliance_series.append((self.tick, report.get("compliance_rate", 0.0)))
        return self.snapshot()

    def _maybe_form_organ(self) -> None:
        if self.tick % 15 != 0 or self.tick == self._last_cluster_tick:
            return
        for cluster in self.network.detect_clusters(min_conductance=0.05):
            members = [
                a for a in self.env.all_agents()
                if a.agent_id in cluster and a.is_differentiated
                and getattr(a, "organ_id", None) is None
            ]
            fresh = [c for c in members if isinstance(c, Cell)]
            if len(fresh) >= 2:
                organ = Organ(founding_cells=fresh[:6])
                self.network.add_agent(organ.organ_id, role=organ.dominant_role.value)
                self.body.register_organ(organ)
                self.organs.append(organ)
                self._last_cluster_tick = self.tick
                break

    # ------------------------------------------------------------------
    # State shaping
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of the whole ecosystem."""
        agents = self.env.all_agents()
        role_counts: dict[str, int] = {}
        for a in agents:
            role_counts[a.role.value] = role_counts.get(a.role.value, 0) + 1

        net = self.network.summary()
        compliance = self.tracker.compliance_summary()
        slos = [
            {
                "name": ev.slo_name,
                "priority": ev.slo_priority,
                "status": ev.status.value,
                "value": round(ev.sli_measurement.value, 4),
            }
            for ev in self.tracker.latest_report().values()
        ]
        recent_events = [
            {"kind": e.kind.value, "source": e.source_agent_id}
            for e in self.mouseion.event_history()[-12:]
        ]

        return {
            "tick": self.tick,
            "agents": {
                "alive": len(agents),
                "differentiated": sum(1 for a in agents if a.is_differentiated),
                "roles": role_counts,
            },
            "network": {
                "nodes": net.get("nodes", 0),
                "edges": net.get("edges", 0),
                "avg_conductance": round(net.get("avg_conductance", 0.0), 4),
                "signals_delivered": net.get("signals_delivered", 0),
            },
            "knowledge": {
                "records": self.mouseion.knowledge_count(),
                "energy_remaining": round(
                    self.mouseion.resource_level(ResourceKind.ENERGY), 1),
            },
            "organs": [o.snapshot() for o in self.body._organs.values()],
            "body": {
                "fully_functional": self.body.is_fully_functional,
                "organs": self.body.organ_count,
                "visions": len(self.body._visions),
            },
            "sla": {
                "compliant": compliance.get("sla_compliant", True),
                "compliance_rate": compliance.get("compliance_rate", 1.0),
                "meeting": compliance.get("meeting", 0),
                "breached": compliance.get("breached", 0),
                "slos": slos,
            },
            "events": recent_events,
        }

    def history(self) -> dict[str, list[list[float]]]:
        """Compact time-series for charts."""
        return {
            "knowledge": [[t, v] for t, v in self._knowledge_series],
            "compliance": [[t, round(v, 4)] for t, v in self._compliance_series],
        }
