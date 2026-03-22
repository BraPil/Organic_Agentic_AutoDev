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
    # --- Generic roles ---
    AgentRole.RESEARCHER: [AgentRole.SYNTHESIZER, AgentRole.CURATOR, AgentRole.CODER],
    AgentRole.CODER: [AgentRole.CRITIC, AgentRole.RESEARCHER, AgentRole.INNOVATOR],
    AgentRole.CRITIC: [AgentRole.CODER, AgentRole.RESEARCHER, AgentRole.GUARDIAN],
    AgentRole.SYNTHESIZER: [AgentRole.RESEARCHER, AgentRole.CONNECTOR, AgentRole.CURATOR],
    AgentRole.CURATOR: [AgentRole.RESEARCHER, AgentRole.SYNTHESIZER, AgentRole.GUARDIAN],
    AgentRole.CONNECTOR: [AgentRole.SYNTHESIZER, AgentRole.INNOVATOR, AgentRole.RESEARCHER],
    AgentRole.INNOVATOR: [AgentRole.CODER, AgentRole.CONNECTOR, AgentRole.RESEARCHER],
    AgentRole.GUARDIAN: [AgentRole.CRITIC, AgentRole.CURATOR, AgentRole.CONNECTOR],

    # --- Oncology / Medical specialist roles (ExMorbus) ---
    # Tumor Board cluster: oncologist sits at the centre
    AgentRole.ONCOLOGIST: [
        AgentRole.PATHOLOGIST, AgentRole.GENETICIST, AgentRole.RADIOLOGIST,
        AgentRole.SYNTHESIZER, AgentRole.CLINICAL_TRIALIST,
    ],
    AgentRole.PATHOLOGIST: [
        AgentRole.ONCOLOGIST, AgentRole.GENETICIST, AgentRole.RADIOLOGIST,
        AgentRole.CRITIC,
    ],
    AgentRole.CLINICAL_TRIALIST: [
        AgentRole.ONCOLOGIST, AgentRole.EPIDEMIOLOGIST, AgentRole.GUARDIAN,
        AgentRole.PATIENT_ADVOCATE,
    ],
    AgentRole.GENETICIST: [
        AgentRole.ONCOLOGIST, AgentRole.PATHOLOGIST, AgentRole.CLINICAL_TRIALIST,
        AgentRole.RESEARCHER,
    ],
    AgentRole.PHARMACOLOGIST: [
        AgentRole.GUARDIAN, AgentRole.CLINICAL_TRIALIST, AgentRole.ONCOLOGIST,
        AgentRole.CURATOR,
    ],
    AgentRole.RADIOLOGIST: [
        AgentRole.ONCOLOGIST, AgentRole.PATHOLOGIST, AgentRole.SYNTHESIZER,
        AgentRole.CLINICAL_TRIALIST,
    ],
    AgentRole.PATIENT_ADVOCATE: [
        AgentRole.GUARDIAN, AgentRole.CONNECTOR, AgentRole.CLINICAL_TRIALIST,
        AgentRole.ONCOLOGIST,
    ],
    AgentRole.EPIDEMIOLOGIST: [
        AgentRole.RESEARCHER, AgentRole.CLINICAL_TRIALIST, AgentRole.SYNTHESIZER,
        AgentRole.INNOVATOR,
    ],
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
        # --- Medical specialist roles (ExMorbus) ---
        elif self.role == AgentRole.ONCOLOGIST:
            self._oncologist_action(env)
        elif self.role == AgentRole.PATHOLOGIST:
            self._pathologist_action(env)
        elif self.role == AgentRole.CLINICAL_TRIALIST:
            self._clinical_trialist_action(env)
        elif self.role == AgentRole.GENETICIST:
            self._geneticist_action(env)
        elif self.role == AgentRole.PHARMACOLOGIST:
            self._pharmacologist_action(env)
        elif self.role == AgentRole.RADIOLOGIST:
            self._radiologist_action(env)
        elif self.role == AgentRole.PATIENT_ADVOCATE:
            self._patient_advocate_action(env)
        elif self.role == AgentRole.EPIDEMIOLOGIST:
            self._epidemiologist_action(env)

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

    # ------------------------------------------------------------------
    # Medical / Oncology role actions (ExMorbus)
    # ------------------------------------------------------------------

    def _oncologist_action(self, env: "Environment") -> None:
        """Synthesise multi-modal data (genomic + pathology + imaging) into a treatment
        recommendation.  High compassion drives thoroughness; high persistence drives
        follow-up on incomplete cases."""
        if self.rng.random() < 0.25 * self.genome.compassion:
            # Gather inputs from multiple oncology knowledge tags
            sources: list[str] = []
            for tag in ("genomics", "pathology", "imaging_finding", "treatment_protocol"):
                recs = env.mouseion.query_knowledge(tag)[:2]
                sources.extend(r.record_id for r in recs)

            confidence = clamp(0.5 + self.specialisation_score * 0.4 + self.genome.compassion * 0.1)
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[Oncologist] Treatment synthesis at tick {env.tick_count}: "
                    f"Integrated {len(sources)} oncological evidence records "
                    f"(spec={self.specialisation_score:.2f}). "
                    "Recommendation: evidence-guided multi-modal treatment approach."
                ),
                topic_tags=["oncology", "treatment_recommendation", "synthesis"],
                confidence=confidence,
                provenance_refs=sources,
            )
            if self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.KNOWLEDGE,
                    source_id=self.agent_id,
                    strength=0.75,
                    payload={"record_id": record.record_id, "domain": "oncology"},
                ), self.agent_id)

    def _pathologist_action(self, env: "Environment") -> None:
        """Analyse pathology records and produce histological interpretations.
        High specialisation → higher confidence diagnoses."""
        if self.rng.random() < 0.30 * self.genome.persistence:
            confidence = clamp(0.6 + self.specialisation_score * 0.35)
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[Pathologist] Histological analysis at tick {env.tick_count}: "
                    f"Tissue specimen evaluation; morphological assessment complete "
                    f"(spec={self.specialisation_score:.2f}). "
                    "IHC panel applied; grade and margins assessed."
                ),
                topic_tags=["pathology", "histology", "oncology", "ihc"],
                confidence=confidence,
            )

    def _clinical_trialist_action(self, env: "Environment") -> None:
        """Identify trial-eligible patients and manage clinical trial data.
        High cooperation → better patient-trial matching broadcasts."""
        if self.rng.random() < 0.20 * self.genome.curiosity:
            genomic_recs = env.mouseion.query_knowledge("genomics")[:3]
            sources = [r.record_id for r in genomic_recs]
            confidence = clamp(0.55 + self.specialisation_score * 0.30 + self.genome.cooperation * 0.15)
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[ClinicalTrialist] Trial matching at tick {env.tick_count}: "
                    f"Screened cohort against {len(sources)} biomarker profiles. "
                    "Identified eligible patients for active oncology trials."
                ),
                topic_tags=["clinical_trial", "trial_matching", "oncology"],
                confidence=confidence,
                provenance_refs=sources,
            )
            if self._network and self.genome.cooperation > 0.5:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.OPPORTUNITY,
                    source_id=self.agent_id,
                    strength=0.65 * self.genome.cooperation,
                    payload={"record_id": record.record_id, "domain": "trial_matching"},
                ), self.agent_id)

    def _geneticist_action(self, env: "Environment") -> None:
        """Interpret genomic variant panels and annotate pathogenicity.
        High curiosity drives discovery; high specialisation drives accuracy."""
        if self.rng.random() < 0.28 * self.genome.curiosity:
            confidence = clamp(0.65 + self.specialisation_score * 0.30)
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[Geneticist] Genomic interpretation at tick {env.tick_count}: "
                    f"NGS variant analysis complete (spec={self.specialisation_score:.2f}). "
                    "Pathogenic/likely-pathogenic variants tiered; actionable mutations flagged."
                ),
                topic_tags=["genomics", "variant_interpretation", "oncology", "ngs"],
                confidence=confidence,
            )
            if self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.KNOWLEDGE,
                    source_id=self.agent_id,
                    strength=0.7,
                    payload={"record_id": record.record_id, "domain": "genomics"},
                ), self.agent_id)

    def _pharmacologist_action(self, env: "Environment") -> None:
        """Check drug interactions and assess toxicity profiles.
        Low risk_tolerance → more conservative safety checks; high resilience
        → detects subtle interaction patterns."""
        if self.rng.random() < 0.25 * self.genome.resilience:
            agents = env.all_agents()
            # Scan for any low-energy agents that might signal toxicity
            struggling = [a for a in agents if 0 < a.energy < 4.0]
            danger_flag = len(struggling) > 0
            confidence = clamp(0.70 + self.specialisation_score * 0.25)
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[Pharmacologist] Drug safety review at tick {env.tick_count}: "
                    f"{'⚠ Potential toxicity signal detected — ' + str(len(struggling)) + ' agents struggling.' if danger_flag else 'No critical interactions identified.'} "
                    f"Concomitant medication review complete (spec={self.specialisation_score:.2f})."
                ),
                topic_tags=["pharmacology", "drug_safety", "toxicity", "oncology"],
                confidence=confidence,
            )
            if danger_flag and self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.DANGER,
                    source_id=self.agent_id,
                    strength=0.85,
                    payload={"record_id": record.record_id, "domain": "drug_safety"},
                ), self.agent_id)

    def _radiologist_action(self, env: "Environment") -> None:
        """Perform RECIST/iRECIST imaging response assessment.
        High specialisation → more accurate tumour measurement."""
        if self.rng.random() < 0.28 * self.genome.specialisation:
            imaging_refs = [r.record_id for r in env.mouseion.query_knowledge("imaging_finding")[:2]]
            confidence = clamp(0.65 + self.specialisation_score * 0.30)
            env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[Radiologist] Imaging assessment at tick {env.tick_count}: "
                    f"RECIST 1.1 tumour measurement applied to {len(imaging_refs)} baseline references. "
                    f"Response category assigned (spec={self.specialisation_score:.2f})."
                ),
                topic_tags=["radiology", "recist", "imaging_finding", "response_assessment", "oncology"],
                confidence=confidence,
                provenance_refs=imaging_refs,
            )

    def _patient_advocate_action(self, env: "Environment") -> None:
        """Monitor patient outcomes and flag quality-of-life deterioration.
        High compassion → proactive palliative care integration signal."""
        if self.rng.random() < 0.30 * self.genome.compassion:
            agents = env.all_agents()
            low_wellbeing = [a for a in agents if a.energy < 5.0]
            needs_support = len(low_wellbeing) > 0
            confidence = clamp(0.60 + self.genome.compassion * 0.25)
            record = env.mouseion.store_knowledge(
                author_id=self.agent_id,
                content=(
                    f"[PatientAdvocate] QoL assessment at tick {env.tick_count}: "
                    f"{'⚠ ' + str(len(low_wellbeing)) + ' agents require wellbeing support — palliative integration recommended.' if needs_support else 'Cohort QoL within acceptable range.'} "
                    f"Patient-centred outcomes tracked (compassion={self.genome.compassion:.2f})."
                ),
                topic_tags=["patient_outcomes", "quality_of_life", "palliative_care", "oncology"],
                confidence=confidence,
            )
            if needs_support and self._network:
                self._network.broadcast(Signal(
                    signal_id=new_id("sig_"),
                    signal_type=SignalType.FOOD,
                    source_id=self.agent_id,
                    strength=0.6 * self.genome.compassion,
                    payload={"record_id": record.record_id, "domain": "patient_support"},
                ), self.agent_id)

    def _epidemiologist_action(self, env: "Environment") -> None:
        """Analyse population-level patterns across the cohort.
        High curiosity drives discovery of novel associations."""
        if self.rng.random() < 0.18 * self.genome.curiosity:
            # Aggregate across multiple knowledge domains
            all_records = list(env.mouseion.all_knowledge())
            domain_tags = {"genomics", "pathology", "clinical_trial", "treatment_protocol", "oncology"}
            relevant = [r for r in all_records if any(t in r.topic_tags for t in domain_tags)]
            if len(relevant) >= 3:
                confidence = clamp(0.55 + self.specialisation_score * 0.25 + self.genome.creativity * 0.2)
                env.mouseion.store_knowledge(
                    author_id=self.agent_id,
                    content=(
                        f"[Epidemiologist] Cohort analysis at tick {env.tick_count}: "
                        f"Pattern scan across {len(relevant)} oncology records. "
                        f"Population-level associations identified "
                        f"(spec={self.specialisation_score:.2f}, curiosity={self.genome.curiosity:.2f})."
                    ),
                    topic_tags=["epidemiology", "cohort_analysis", "oncology", "population_patterns"],
                    confidence=confidence,
                    provenance_refs=[r.record_id for r in relevant[:5]],
                )

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
