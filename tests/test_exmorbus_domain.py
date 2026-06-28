"""
tests/test_exmorbus_domain.py — Tests for the ExMorbus medical domain module.

Covers:
  - MedicalKnowledgeRecordV0 and ClinicalEvidenceLevel contracts
  - seed_mouseion() — content, confidence levels, tag coverage
  - create_medical_niches() — correct roles, urgency order, reward structure
  - create_medical_genome() — trait profiles, value ranges, invalid role rejection
  - genome affinity with medical niches
  - Medical cell role actions (oncologist, pathologist, etc.)
"""

from __future__ import annotations

import random

import pytest

from organic_agentic_autodev.core.environment import Environment
from organic_agentic_autodev.core.genome import Genome
from organic_agentic_autodev.domain.exmorbus.contracts import (
    AdverseEventSeverity,
    ClinicalEvidenceLevel,
    MedicalKnowledgeRecordV0,
    MedicalKnowledgeType,
    OncologyDomain,
)
from organic_agentic_autodev.domain.exmorbus.genome_profiles import (
    MEDICAL_ROLE_BIAS,
    all_medical_roles,
    create_medical_genome,
)
from organic_agentic_autodev.domain.exmorbus.niches import create_medical_niches, _MEDICAL_NICHE_SPECS
from organic_agentic_autodev.domain.exmorbus.seeder import (
    EXMORBUS_SEED_AUTHOR,
    _SEED_ENTRIES,
    seed_mouseion,
    seed_summary,
)
from organic_agentic_autodev.mouseion.contracts import AgentRole, ResourceKind
from organic_agentic_autodev.mouseion.substrate import Mouseion
from organic_agentic_autodev.organisms.cell import Cell


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_env(seed: int = 0) -> tuple[Mouseion, Environment]:
    rng = random.Random(seed)
    mouseion = Mouseion()
    env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
    return mouseion, env


# ---------------------------------------------------------------------------
# ClinicalEvidenceLevel contracts
# ---------------------------------------------------------------------------

class TestClinicalEvidenceLevel:
    def test_rct_has_highest_weight(self):
        assert ClinicalEvidenceLevel.RCT.confidence_weight == 1.0

    def test_expert_opinion_has_lower_weight_than_rct(self):
        rct = ClinicalEvidenceLevel.RCT.confidence_weight
        eo = ClinicalEvidenceLevel.EXPERT_OPINION.confidence_weight
        assert eo < rct

    def test_all_weights_in_valid_range(self):
        for level in ClinicalEvidenceLevel:
            w = level.confidence_weight
            assert 0.0 < w <= 1.0, f"{level}: weight {w} out of range"

    def test_preclinical_is_lowest(self):
        weights = {level: level.confidence_weight for level in ClinicalEvidenceLevel}
        min_level = min(weights, key=lambda k: weights[k])
        assert min_level == ClinicalEvidenceLevel.PRECLINICAL


# ---------------------------------------------------------------------------
# MedicalKnowledgeRecordV0
# ---------------------------------------------------------------------------

class TestMedicalKnowledgeRecord:
    def test_effective_confidence_blends_significance_and_evidence(self):
        record = MedicalKnowledgeRecordV0(
            base_record_id="test_001",
            knowledge_type=MedicalKnowledgeType.GENOMIC_PROFILE,
            evidence_level=ClinicalEvidenceLevel.RCT,
            clinical_significance=0.9,
        )
        # RCT weight = 1.0, so effective = 0.9 * 1.0 = 0.9
        assert abs(record.effective_confidence - 0.9) < 0.001

    def test_expert_opinion_reduces_effective_confidence(self):
        record_rct = MedicalKnowledgeRecordV0(
            base_record_id="r1",
            knowledge_type=MedicalKnowledgeType.TREATMENT_PROTOCOL,
            evidence_level=ClinicalEvidenceLevel.RCT,
            clinical_significance=0.8,
        )
        record_eo = MedicalKnowledgeRecordV0(
            base_record_id="r2",
            knowledge_type=MedicalKnowledgeType.TREATMENT_PROTOCOL,
            evidence_level=ClinicalEvidenceLevel.EXPERT_OPINION,
            clinical_significance=0.8,
        )
        assert record_eo.effective_confidence < record_rct.effective_confidence

    def test_effective_confidence_capped_at_one(self):
        record = MedicalKnowledgeRecordV0(
            base_record_id="r3",
            knowledge_type=MedicalKnowledgeType.GUIDELINE,
            evidence_level=ClinicalEvidenceLevel.RCT,
            clinical_significance=1.0,
        )
        assert record.effective_confidence <= 1.0

    def test_all_knowledge_types_instantiate(self):
        for ktype in MedicalKnowledgeType:
            r = MedicalKnowledgeRecordV0(
                base_record_id="x",
                knowledge_type=ktype,
            )
            assert r.knowledge_type == ktype

    def test_guideline_aligned_field(self):
        record = MedicalKnowledgeRecordV0(
            base_record_id="r4",
            knowledge_type=MedicalKnowledgeType.GUIDELINE,
            guideline_aligned=True,
        )
        assert record.guideline_aligned is True


# ---------------------------------------------------------------------------
# ExMorbus Seeder
# ---------------------------------------------------------------------------

class TestExMorbusSeeder:
    def setup_method(self):
        self.mouseion = Mouseion()
        self.pairs = seed_mouseion(self.mouseion)

    def test_seeds_20_records(self):
        assert len(self.pairs) == 20

    def test_all_records_in_mouseion(self):
        count = self.mouseion.knowledge_count()
        assert count == 20

    def test_author_is_exmorbus_seeder(self):
        for base, _ in self.pairs:
            assert base.author_id == EXMORBUS_SEED_AUTHOR

    def test_all_records_have_valid_confidence(self):
        for base, _ in self.pairs:
            assert 0.0 <= base.confidence <= 1.0, (
                f"Record {base.record_id} has confidence {base.confidence}"
            )

    def test_mean_confidence_above_threshold(self):
        confs = [b.confidence for b, _ in self.pairs]
        mean_conf = sum(confs) / len(confs)
        assert mean_conf >= 0.85, f"Mean confidence {mean_conf:.3f} below 0.85"

    def test_medical_metadata_attached(self):
        for _, meta in self.pairs:
            assert isinstance(meta, MedicalKnowledgeRecordV0)
            assert meta.base_record_id

    def test_all_oncology_domains_represented(self):
        domains = {meta.oncology_domain for _, meta in self.pairs}
        assert OncologyDomain.GENERAL in domains
        assert len(domains) >= 4, f"Only {len(domains)} domains represented"

    def test_all_knowledge_types_present(self):
        types = {meta.knowledge_type for _, meta in self.pairs}
        expected = {
            MedicalKnowledgeType.GENOMIC_PROFILE,
            MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
            MedicalKnowledgeType.TREATMENT_PROTOCOL,
            MedicalKnowledgeType.ADVERSE_EVENT,
            MedicalKnowledgeType.IMAGING_FINDING,
            MedicalKnowledgeType.CLINICAL_TRIAL,
            MedicalKnowledgeType.GUIDELINE,
        }
        missing = expected - types
        assert not missing, f"Knowledge types missing from seed: {missing}"

    def test_queryable_by_genomics_tag(self):
        records = self.mouseion.query_knowledge("genomics")
        assert len(records) >= 3, "Expected at least 3 genomics records"

    def test_queryable_by_treatment_tag(self):
        records = self.mouseion.query_knowledge("treatment_protocol")
        assert len(records) >= 1

    def test_queryable_by_adverse_event_tag(self):
        records = self.mouseion.query_knowledge("adverse_event")
        assert len(records) >= 3

    def test_seed_summary_structure(self):
        summary = seed_summary(self.pairs)
        assert "total_records" in summary
        assert "mean_confidence" in summary
        assert "by_type" in summary
        assert "by_domain" in summary
        assert summary["total_records"] == 20

    def test_validated_review_status(self):
        for _, meta in self.pairs:
            assert meta.review_status == "validated"

    def test_guideline_aligned_true(self):
        for _, meta in self.pairs:
            assert meta.guideline_aligned is True

    def test_idempotent_second_seed_adds_more_records(self):
        """Calling seed_mouseion twice doubles the record count (not deduplicated at this layer)."""
        second_pairs = seed_mouseion(self.mouseion)
        assert self.mouseion.knowledge_count() == 40


# ---------------------------------------------------------------------------
# Medical Niches
# ---------------------------------------------------------------------------

class TestMedicalNiches:
    def setup_method(self):
        self.niches = create_medical_niches()

    def test_creates_12_niches(self):
        assert len(self.niches) == 12

    def test_all_niches_open(self):
        for niche in self.niches:
            assert niche.is_open

    def test_niches_have_unique_ids(self):
        ids = [n.niche_id for n in self.niches]
        assert len(ids) == len(set(ids))

    def test_guardian_niche_highest_urgency(self):
        guardian_niches = [n for n in self.niches if n.role == AgentRole.GUARDIAN]
        assert guardian_niches, "GUARDIAN niche must exist"
        max_urgency = max(n.urgency for n in self.niches)
        assert any(n.urgency >= max_urgency - 0.01 for n in guardian_niches)

    def test_all_medical_roles_covered(self):
        from organic_agentic_autodev.domain.exmorbus.genome_profiles import MEDICAL_ROLE_BIAS
        niche_roles = {n.role for n in self.niches}
        medical_roles = set(MEDICAL_ROLE_BIAS.keys())
        missing = medical_roles - niche_roles
        assert not missing, f"Medical roles without niches: {missing}"

    def test_all_niches_have_rewards(self):
        for niche in self.niches:
            assert niche.base_reward, f"Niche {niche.niche_id} has no reward"

    def test_urgency_in_valid_range(self):
        for niche in self.niches:
            assert 0.0 <= niche.urgency <= 1.0

    def test_urgency_growth_rate_positive(self):
        for niche in self.niches:
            assert niche.urgency_growth_rate > 0

    def test_niches_integrate_with_environment(self):
        mouseion = Mouseion()
        env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=random.Random(0))
        env.seed_niches(self.niches)
        assert len(env.open_niches()) == 12

    def test_genome_affinity_works_with_medical_niches(self):
        from organic_agentic_autodev.core.genome import Genome
        genome = Genome(curiosity=0.9, creativity=0.9, persistence=0.8,
                        risk_tolerance=0.3, cooperation=0.6, specialisation=0.7,
                        compassion=0.7, resilience=0.6)
        for niche in self.niches:
            affinity = niche.genome_affinity(genome)
            assert 0.0 <= affinity <= 1.0


# ---------------------------------------------------------------------------
# Medical Genome Profiles
# ---------------------------------------------------------------------------

class TestMedicalGenomeProfiles:
    def test_all_medical_roles_have_bias(self):
        for role in all_medical_roles():
            assert role in MEDICAL_ROLE_BIAS

    def test_create_genome_for_all_medical_roles(self):
        rng = random.Random(42)
        for role in all_medical_roles():
            genome = create_medical_genome(role, rng=rng)
            assert isinstance(genome, Genome)

    def test_all_traits_in_valid_range(self):
        rng = random.Random(99)
        for role in all_medical_roles():
            genome = create_medical_genome(role, rng=rng)
            for trait in Genome._trait_names():
                val = getattr(genome, trait)
                assert 0.0 <= val <= 1.0, (
                    f"{role.value}.{trait} = {val} out of [0, 1]"
                )

    def test_oncologist_high_compassion(self):
        """Oncologist genomes should have compassion significantly above 0.5."""
        rng = random.Random(0)
        samples = [create_medical_genome(AgentRole.ONCOLOGIST, rng=rng).compassion
                   for _ in range(30)]
        assert sum(samples) / len(samples) > 0.70

    def test_pathologist_high_specialisation(self):
        rng = random.Random(1)
        samples = [create_medical_genome(AgentRole.PATHOLOGIST, rng=rng).specialisation
                   for _ in range(30)]
        assert sum(samples) / len(samples) > 0.70

    def test_patient_advocate_high_cooperation(self):
        rng = random.Random(2)
        samples = [create_medical_genome(AgentRole.PATIENT_ADVOCATE, rng=rng).cooperation
                   for _ in range(30)]
        assert sum(samples) / len(samples) > 0.70

    def test_radiologist_low_risk_tolerance(self):
        rng = random.Random(3)
        samples = [create_medical_genome(AgentRole.RADIOLOGIST, rng=rng).risk_tolerance
                   for _ in range(30)]
        assert sum(samples) / len(samples) < 0.45

    def test_invalid_role_raises_value_error(self):
        with pytest.raises(ValueError, match="not a medical role"):
            create_medical_genome(AgentRole.STEM_CELL)

    def test_differentiation_threshold_below_default(self):
        """Medical genomes should differentiate slightly faster than the default 0.7."""
        rng = random.Random(7)
        for role in all_medical_roles():
            genome = create_medical_genome(role, rng=rng)
            assert genome.differentiation_threshold <= 0.70

    def test_reproducibility_with_seeded_rng(self):
        g1 = create_medical_genome(AgentRole.ONCOLOGIST, rng=random.Random(12))
        g2 = create_medical_genome(AgentRole.ONCOLOGIST, rng=random.Random(12))
        assert g1.compassion == g2.compassion
        assert g1.persistence == g2.persistence


# ---------------------------------------------------------------------------
# Medical Cell Role Actions
# ---------------------------------------------------------------------------

class TestMedicalCellActions:
    def setup_method(self):
        mouseion = Mouseion(initial_resources={k: 500.0 for k in ResourceKind})
        niches = create_medical_niches()
        rng = random.Random(77)
        env = Environment(mouseion=mouseion, neighbourhood_radius=100, rng=rng)
        env.seed_niches(niches)
        seed_mouseion(mouseion)
        self.mouseion = mouseion
        self.env = env

    def _make_cell(self, role: AgentRole, energy: float = 30.0) -> Cell:
        rng = random.Random(42)
        genome = create_medical_genome(role, rng=random.Random(0))
        cell = Cell(role=role, genome=genome, initial_energy=energy, rng=rng)
        self.env.register(cell)
        return cell

    def _run_steps(self, cell: Cell, n: int = 20) -> None:
        for _ in range(n):
            cell.step(self.env)

    def test_oncologist_produces_knowledge(self):
        cell = self._make_cell(AgentRole.ONCOLOGIST)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_pathologist_produces_knowledge(self):
        cell = self._make_cell(AgentRole.PATHOLOGIST)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_clinical_trialist_produces_knowledge(self):
        cell = self._make_cell(AgentRole.CLINICAL_TRIALIST)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_geneticist_produces_genomics_records(self):
        initial_genomics = len(self.mouseion.query_knowledge("genomics"))
        cell = self._make_cell(AgentRole.GENETICIST)
        self._run_steps(cell, 40)
        assert len(self.mouseion.query_knowledge("genomics")) > initial_genomics

    def test_pharmacologist_produces_knowledge(self):
        cell = self._make_cell(AgentRole.PHARMACOLOGIST)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_radiologist_produces_radiology_records(self):
        cell = self._make_cell(AgentRole.RADIOLOGIST)
        self._run_steps(cell, 40)
        radiology = self.mouseion.query_knowledge("radiology")
        recist = self.mouseion.query_knowledge("recist")
        assert len(radiology) + len(recist) > 0

    def test_patient_advocate_produces_knowledge(self):
        cell = self._make_cell(AgentRole.PATIENT_ADVOCATE)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_epidemiologist_produces_knowledge(self):
        cell = self._make_cell(AgentRole.EPIDEMIOLOGIST)
        initial = self.mouseion.knowledge_count()
        self._run_steps(cell, 40)
        assert self.mouseion.knowledge_count() > initial

    def test_all_medical_cells_survive_40_steps(self):
        """Medical cells with sufficient energy should survive 40 steps."""
        for role in all_medical_roles():
            cell = self._make_cell(role, energy=50.0)
            self._run_steps(cell, 40)
            assert cell.energy > 0, f"{role.value} cell died before 40 steps"

    def test_specialisation_increases_with_activity(self):
        cell = self._make_cell(AgentRole.ONCOLOGIST, energy=50.0)
        initial_spec = cell.specialisation_score
        self._run_steps(cell, 30)
        assert cell.specialisation_score > initial_spec
