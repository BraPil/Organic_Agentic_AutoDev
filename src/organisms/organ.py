"""
src/organisms/organ.py

Organ — a functional cluster of aligned Cells.

An Organ emerges when the slime mold network's cluster detection identifies
a strongly connected group of compatible Cells.  It is NOT explicitly
created by a designer — it forms from the bottom up.

Once formed, an Organ:
  - Has a collective function (ResearchOrgan, BuildOrgan, EvaluationOrgan, etc.)
  - Coordinates its member Cells toward shared goals
  - Manages its own energy budget (shared pool for the organ)
  - Can grow (recruit new Cells) or shrink (lose under-performing Cells)
  - Reports its output up to the Body
  - Can dissolve if member cells die or disperse

The dominant role among member cells determines the organ's functional type.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import TYPE_CHECKING

from src.mouseion.contracts import AgentRole, EventEnvelopeV0, EventKind, ResourceKind
from src.utils.helpers import get_logger, new_id, now_ms

if TYPE_CHECKING:
    from src.core.environment import Environment
    from src.organisms.cell import Cell

logger = get_logger("organ")

# Minimum cells required to form a stable organ
MIN_ORGAN_SIZE = 2
# Maximum cells in a single organ (specialised, not sprawling)
MAX_ORGAN_SIZE = 12


class Organ:
    """
    A functional collective of differentiated Cells.

    Parameters
    ----------
    founding_cells:
        Initial set of Cells that seed this organ.
    organ_id:
        Unique identifier (auto-generated if None).
    """

    def __init__(
        self,
        founding_cells: list["Cell"],
        organ_id: str | None = None,
    ) -> None:
        self.organ_id: str = organ_id or new_id("org_")
        self._cells: dict[str, "Cell"] = {}
        self._dominant_role: AgentRole = AgentRole.STEM_CELL
        self._shared_energy: float = 0.0
        self._age_ticks: int = 0
        self._output_records: list[str] = []  # knowledge record IDs produced
        self._created_at_ms: int = now_ms()

        for cell in founding_cells:
            self.add_cell(cell)

        logger.info("Organ %s formed with %d founding cells, dominant role: %s",
                    self.organ_id, len(founding_cells), self._dominant_role.value)

    # ------------------------------------------------------------------
    # Cell membership
    # ------------------------------------------------------------------

    def add_cell(self, cell: "Cell") -> bool:
        if len(self._cells) >= MAX_ORGAN_SIZE:
            logger.debug("Organ %s at capacity, cannot add cell %s", self.organ_id, cell.agent_id)
            return False
        self._cells[cell.agent_id] = cell
        cell.join_organ(self.organ_id)
        self._recalculate_dominant_role()
        logger.debug("Cell %s added to organ %s", cell.agent_id, self.organ_id)
        return True

    def remove_cell(self, cell_id: str) -> None:
        cell = self._cells.pop(cell_id, None)
        if cell:
            cell.leave_organ()
            self._recalculate_dominant_role()

    def _recalculate_dominant_role(self) -> None:
        if not self._cells:
            self._dominant_role = AgentRole.STEM_CELL
            return
        role_counts = Counter(cell.role for cell in self._cells.values())
        self._dominant_role = role_counts.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Collective step
    # ------------------------------------------------------------------

    def step(self, env: "Environment") -> dict:
        """
        Coordinate all member cells for one tick.
        Returns a summary of the organ's activity.
        """
        self._age_ticks += 1
        dead_cells: list[str] = []
        active = 0

        for cell_id, cell in list(self._cells.items()):
            if cell.energy <= 0:
                dead_cells.append(cell_id)
            else:
                # Organ redistributes shared energy to struggling cells
                if cell.energy < 3.0 and self._shared_energy > 2.0:
                    transfer = min(2.0, self._shared_energy * 0.2)
                    cell.energy += transfer
                    self._shared_energy -= transfer
                active += 1

        # Remove dead cells
        for cid in dead_cells:
            self.remove_cell(cid)

        # Collect a small levy from well-nourished cells into shared pool
        for cell in self._cells.values():
            if cell.energy > 10.0:
                levy = cell.energy * 0.02
                cell.energy -= levy
                self._shared_energy += levy

        # Emit organ-level synthesis if research organ
        if self._dominant_role == AgentRole.RESEARCHER and self._age_ticks % 5 == 0:
            self._produce_synthesis(env)

        return {
            "organ_id": self.organ_id,
            "role": self._dominant_role.value,
            "cells": len(self._cells),
            "active": active,
            "dead_this_tick": len(dead_cells),
            "shared_energy": round(self._shared_energy, 2),
        }

    def _produce_synthesis(self, env: "Environment") -> None:
        """The organ collectively produces a higher-quality knowledge record."""
        member_ids = list(self._cells.keys())
        avg_spec = statistics.mean(c.specialisation_score for c in self._cells.values()) if self._cells else 0
        record = env.mouseion.store_knowledge(
            author_id=self.organ_id,
            content=(
                f"Organ synthesis at tick {env.tick_count}: "
                f"{len(self._cells)}-cell {self._dominant_role.value} organ output"
            ),
            topic_tags=[self._dominant_role.value, "organ_synthesis", "collective"],
            confidence=min(0.95, 0.5 + avg_spec * 0.5),
            provenance_refs=member_ids,
        )
        self._output_records.append(record.record_id)
        env.mouseion.emit(EventEnvelopeV0(
            event_id=new_id("evt_"),
            kind=EventKind.ORGAN_FORMED,
            source_agent_id=self.organ_id,
            payload={"record_id": record.record_id, "cells": len(self._cells)},
        ))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._cells)

    @property
    def is_viable(self) -> bool:
        return len(self._cells) >= MIN_ORGAN_SIZE

    @property
    def dominant_role(self) -> AgentRole:
        return self._dominant_role

    @property
    def cells(self) -> list["Cell"]:
        return list(self._cells.values())

    @property
    def mean_energy(self) -> float:
        if not self._cells:
            return 0.0
        return statistics.mean(c.energy for c in self._cells.values())

    @property
    def mean_specialisation(self) -> float:
        if not self._cells:
            return 0.0
        return statistics.mean(c.specialisation_score for c in self._cells.values())

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "organ_id": self.organ_id,
            "dominant_role": self._dominant_role.value,
            "size": self.size,
            "is_viable": self.is_viable,
            "mean_energy": round(self.mean_energy, 2),
            "mean_specialisation": round(self.mean_specialisation, 3),
            "shared_energy": round(self._shared_energy, 2),
            "age_ticks": self._age_ticks,
            "knowledge_records_produced": len(self._output_records),
        }

    def __repr__(self) -> str:
        return (
            f"Organ(id={self.organ_id}, role={self._dominant_role.value}, "
            f"cells={self.size}, energy={self.mean_energy:.1f})"
        )
