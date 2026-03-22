"""
src/domain/exmorbus/seeder.py

ExMorbus knowledge seeder — pre-populates the Mouseion with established
oncological knowledge records.

This is the biological equivalent of a zygote's inherited epigenome: before
any agents differentiate, the ecosystem already contains the foundational
knowledge that will guide their behaviour.

The 20 seed records cover:
  - Genomic biomarkers and their clinical actionability
  - Standard treatment protocols (NCCN / ASCO Category 1)
  - Adverse event management guidelines (CTCAE-based)
  - Imaging response criteria (RECIST 1.1, iRECIST)
  - Clinical trial landmark data
  - Prognostic / staging frameworks

Each record includes:
  - Sanitised clinical content (prompt-injection safe)
  - Topic tags for retrieval (by speciality and knowledge type)
  - Confidence score proportional to evidence level
  - Provenance markers (source category)

Usage:
    from src.domain.exmorbus.seeder import seed_mouseion

    mouseion = Mouseion()
    records = seed_mouseion(mouseion)
    print(f"Seeded {len(records)} knowledge records")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.domain.exmorbus.contracts import (
    ClinicalEvidenceLevel,
    MedicalKnowledgeRecordV0,
    MedicalKnowledgeType,
    OncologyDomain,
)
from src.mouseion.contracts import KnowledgeRecordV0
from src.utils.helpers import get_logger, new_id

if TYPE_CHECKING:
    from src.mouseion.substrate import Mouseion

logger = get_logger("exmorbus.seeder")

# Author ID used for all seeded records
EXMORBUS_SEED_AUTHOR = "exmorbus_seeder"


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

@dataclass
class _SeedEntry:
    """Internal definition of a seed knowledge record."""
    content: str
    topic_tags: list[str]
    confidence: float
    knowledge_type: MedicalKnowledgeType
    evidence_level: ClinicalEvidenceLevel
    oncology_domain: OncologyDomain = OncologyDomain.GENERAL
    clinical_significance: float = 0.75
    patient_population: str = ""


_SEED_ENTRIES: list[_SeedEntry] = [

    # ------------------------------------------------------------------
    # Genomic biomarkers
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "BRCA1/BRCA2 pathogenic variants confer 45-72% lifetime breast cancer risk "
            "and 17-44% ovarian cancer risk. Germline testing recommended for hereditary "
            "breast/ovarian cancer syndrome evaluation. PARP inhibitors (olaparib, "
            "rucaparib, niraparib) FDA-approved for BRCA1/2-mutated HER2-negative "
            "metastatic breast cancer."
        ),
        topic_tags=["genomics", "brca", "breast_cancer", "ovarian_cancer", "germline",
                    "parp_inhibitor"],
        confidence=0.95,
        knowledge_type=MedicalKnowledgeType.GENOMIC_PROFILE,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.BREAST,
        clinical_significance=0.95,
        patient_population="BRCA1/2 germline mutation carriers",
    ),

    _SeedEntry(
        content=(
            "EGFR L858R and exon 19 deletion mutations sensitize NSCLC to EGFR TKIs: "
            "first-generation (erlotinib, gefitinib), second-generation (afatinib, dacomitinib), "
            "and third-generation osimertinib (preferred, superior CNS penetration, T790M resistance). "
            "EGFR testing is standard of care for all advanced NSCLC patients."
        ),
        topic_tags=["genomics", "egfr", "nsclc", "lung_cancer", "targeted_therapy", "tki"],
        confidence=0.97,
        knowledge_type=MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.LUNG,
        clinical_significance=0.97,
        patient_population="Advanced NSCLC",
    ),

    _SeedEntry(
        content=(
            "ALK rearrangements occur in approximately 3-5% of NSCLC, predominantly "
            "younger never/light smokers with adenocarcinoma histology. "
            "ALK fusion-positive tumors respond to crizotinib, alectinib (superior CNS penetration), "
            "brigatinib, and lorlatinib (preferred for CNS disease or prior ALK TKI progression). "
            "Testing by FISH, IHC, or NGS; IHC D5F3 is a reliable screening test."
        ),
        topic_tags=["genomics", "alk", "nsclc", "targeted_therapy", "fusion"],
        confidence=0.95,
        knowledge_type=MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.LUNG,
        clinical_significance=0.93,
        patient_population="Advanced NSCLC",
    ),

    _SeedEntry(
        content=(
            "KRAS G12C mutation occurs in approximately 13% of NSCLC and 3% of colorectal cancer. "
            "Sotorasib (AMG 510) and adagrasib (MRTX849) are the first approved KRAS-specific inhibitors "
            "targeting this variant. CodeBreaK 100 trial demonstrated ORR 37.1% for sotorasib in "
            "KRAS G12C NSCLC; KRYSTAL-1 showed ORR 42.9% for adagrasib."
        ),
        topic_tags=["genomics", "kras", "kras_g12c", "nsclc", "colorectal",
                    "targeted_therapy"],
        confidence=0.92,
        knowledge_type=MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.LUNG,
        clinical_significance=0.90,
        patient_population="KRAS G12C-mutated NSCLC or CRC",
    ),

    # ------------------------------------------------------------------
    # Immunotherapy biomarkers
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "Microsatellite instability high (MSI-H) or mismatch repair deficient (dMMR) tumours: "
            "pembrolizumab (anti-PD-1) FDA-approved pan-tumour for unresectable/metastatic MSI-H/dMMR "
            "disease (KEYNOTE-158). Durable responses particularly in colorectal and endometrial cancer. "
            "MSI testing recommended for all colorectal cancer; dMMR testing recommended for "
            "endometrial cancer."
        ),
        topic_tags=["msi-h", "dmmr", "immunotherapy", "pembrolizumab", "biomarker", "pan-tumor"],
        confidence=0.93,
        knowledge_type=MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.93,
    ),

    _SeedEntry(
        content=(
            "Tumour mutational burden (TMB) greater than 10 mutations per megabase: "
            "pembrolizumab FDA-approved for TMB-H unresectable/metastatic solid tumors (KEYNOTE-158). "
            "TMB-H associated with improved response to immune checkpoint inhibitors across tumour types. "
            "TMB testing by tissue NGS or blood-based ctDNA assays. Interpretation varies by tumour type "
            "and assay platform — standardisation ongoing."
        ),
        topic_tags=["tmb", "immunotherapy", "biomarker", "checkpoint_inhibitor", "pembrolizumab"],
        confidence=0.82,
        knowledge_type=MedicalKnowledgeType.BIOMARKER_ASSESSMENT,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.80,
    ),

    # ------------------------------------------------------------------
    # Treatment protocols
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "HER2-positive breast cancer: dual HER2 blockade with trastuzumab + pertuzumab + "
            "docetaxel (THP/Perjeta combination) is standard neoadjuvant/first-line metastatic therapy. "
            "Ado-trastuzumab emtansine (T-DM1) for residual invasive disease post-neoadjuvant. "
            "Trastuzumab deruxtecan (T-DXd) for HER2+ MBC after 1+ prior anti-HER2 regimens. "
            "NCCN Category 1 recommendation."
        ),
        topic_tags=["her2", "breast_cancer", "trastuzumab", "protocol", "treatment",
                    "pertuzumab", "tdm1", "treatment_protocol"],
        confidence=0.96,
        knowledge_type=MedicalKnowledgeType.TREATMENT_PROTOCOL,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.BREAST,
        clinical_significance=0.97,
        patient_population="HER2-positive breast cancer",
    ),

    _SeedEntry(
        content=(
            "Diffuse large B-cell lymphoma (DLBCL) standard first-line: "
            "R-CHOP (rituximab + cyclophosphamide + doxorubicin + vincristine + prednisone) "
            "x 6 cycles achieves 60-70% cure in localised disease. "
            "Polatuzumab vedotin + R-CHP (Pola-R-CHP) preferred for high-risk DLBCL per POLARIX trial. "
            "Relapsed/refractory: CAR-T (axicabtagene ciloleucel, tisagenlecleucel) after 2+ prior lines."
        ),
        topic_tags=["dlbcl", "r-chop", "lymphoma", "protocol", "treatment", "hematologic",
                    "rituximab", "car-t", "treatment_protocol"],
        confidence=0.95,
        knowledge_type=MedicalKnowledgeType.TREATMENT_PROTOCOL,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.HEMATOLOGIC,
        clinical_significance=0.95,
        patient_population="DLBCL, all stages",
    ),

    _SeedEntry(
        content=(
            "CAR-T cell therapy for R/R large B-cell lymphoma: "
            "axicabtagene ciloleucel (axi-cel) and tisagenlecleucel (tisa-cel) FDA-approved "
            "after two or more prior lines. ZUMA-7 trial: axi-cel superior to salvage "
            "chemo in second-line R/R LBCL. Complete remission durable in 40-54%. "
            "Cytokine release syndrome (CRS) and ICANS require specialised monitoring in "
            "certified treatment centres."
        ),
        topic_tags=["cart_therapy", "lymphoma", "immunotherapy", "car-t", "hematologic",
                    "crs", "icans", "treatment_protocol"],
        confidence=0.90,
        knowledge_type=MedicalKnowledgeType.TREATMENT_PROTOCOL,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.HEMATOLOGIC,
        clinical_significance=0.92,
        patient_population="Relapsed/refractory large B-cell lymphoma",
    ),

    # ------------------------------------------------------------------
    # Adverse event management
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "Immune-related adverse events (irAEs) from checkpoint inhibitors (anti-CTLA4, anti-PD-1/L1): "
            "colitis (most common with anti-CTLA4), pneumonitis (anti-PD-1/L1), hepatitis, "
            "endocrinopathies (thyroiditis, adrenal insufficiency, hypophysitis), and dermatitis. "
            "Management: Grade 1-2 — continue with monitoring and supportive care. "
            "Grade 3-4 — hold treatment, systemic corticosteroids (prednisone 1-2 mg/kg/day), "
            "infliximab for steroid-refractory colitis. Most irAEs are reversible."
        ),
        topic_tags=["immunotherapy", "adverse_event", "irae", "checkpoint_inhibitor",
                    "toxicity", "colitis", "pneumonitis"],
        confidence=0.94,
        knowledge_type=MedicalKnowledgeType.ADVERSE_EVENT,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.95,
    ),

    _SeedEntry(
        content=(
            "Cardiotoxicity from anthracyclines (doxorubicin, epirubicin): "
            "cumulative dose-dependent cardiomyopathy. Lifetime doxorubicin limit approximately "
            "450-550 mg/m². Baseline LVEF assessment required before starting; monitor LVEF "
            "every 3 cycles in high-risk patients (prior cardiac disease, hypertension). "
            "Dexrazoxane is cardioprotective for high cumulative doses. "
            "Subclinical cardiac dysfunction detectable by cardiac biomarkers (troponin, BNP)."
        ),
        topic_tags=["cardiotoxicity", "anthracycline", "doxorubicin", "adverse_event",
                    "toxicity", "lvef"],
        confidence=0.90,
        knowledge_type=MedicalKnowledgeType.ADVERSE_EVENT,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.92,
    ),

    _SeedEntry(
        content=(
            "Neutropenic fever: oncologic emergency. Definition: ANC < 500 cells/mm³ + "
            "fever ≥ 38.3°C (or ≥ 38.0°C sustained > 1 hour). "
            "Empiric broad-spectrum antibiotics within 1 hour of presentation (piperacillin-tazobactam "
            "or cefepime; add vancomycin for catheter-related infection risk). "
            "High-risk features (MASCC score < 21): IV antibiotics and hospitalisation required. "
            "G-CSF prophylaxis recommended when febrile neutropenia risk > 20%."
        ),
        topic_tags=["neutropenic_fever", "emergency", "adverse_event", "antibiotic",
                    "protocol", "g-csf"],
        confidence=0.96,
        knowledge_type=MedicalKnowledgeType.ADVERSE_EVENT,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.97,
    ),

    _SeedEntry(
        content=(
            "Tumour lysis syndrome (TLS) prevention: high-risk in bulky haematological malignancies "
            "(Burkitt lymphoma, ALL, aggressive NHL, AML with high WBC). "
            "Prophylaxis: allopurinol (low-moderate risk) or rasburicase (high-risk or established TLS). "
            "Aggressive IV hydration 200-300 mL/hr. "
            "Monitor every 6-8 hours: uric acid, LDH, potassium, phosphate, calcium, creatinine. "
            "Avoid drugs that raise potassium or phosphate in high-risk period."
        ),
        topic_tags=["tls", "tumor_lysis_syndrome", "hematologic", "emergency", "adverse_event",
                    "prophylaxis"],
        confidence=0.95,
        knowledge_type=MedicalKnowledgeType.ADVERSE_EVENT,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.HEMATOLOGIC,
        clinical_significance=0.96,
    ),

    # ------------------------------------------------------------------
    # Imaging response criteria
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "RECIST 1.1 criteria for solid tumour response assessment: "
            "Complete Response (CR): disappearance of all target lesions, short axis lymph nodes < 10 mm. "
            "Partial Response (PR): ≥ 30% decrease in sum of diameters from baseline. "
            "Progressive Disease (PD): ≥ 20% increase (≥ 5 mm absolute) or new measurable lesion. "
            "Stable Disease (SD): neither PR nor PD criteria met. "
            "Maximum 5 target lesions total, 2 per organ; minimum 10 mm for target lesions."
        ),
        topic_tags=["recist", "imaging_finding", "response_assessment", "ct", "guideline"],
        confidence=0.98,
        knowledge_type=MedicalKnowledgeType.IMAGING_FINDING,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.98,
    ),

    _SeedEntry(
        content=(
            "iRECIST for immunotherapy trials: addresses pseudoprogression seen in 3-10% of patients. "
            "Unconfirmed Progressive Disease (iUPD): possible progression, continue treatment, "
            "confirm or deny at next assessment 4-8 weeks later. "
            "Confirmed Progressive Disease (iCPD): true progression, discontinue immunotherapy. "
            "Unconfirmed Complete/Partial Response (iCR, iPR) and Stable Disease (iSD) equivalent to RECIST."
        ),
        topic_tags=["irecist", "imaging_finding", "immunotherapy", "pseudoprogression", "guideline"],
        confidence=0.88,
        knowledge_type=MedicalKnowledgeType.IMAGING_FINDING,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.85,
        patient_population="Patients on immune checkpoint inhibitors",
    ),

    # ------------------------------------------------------------------
    # Clinical trial landmark data
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "KEYNOTE-158 (pembrolizumab pan-tumour, TMB-H cohorts): "
            "ORR 29% across 10 tumour types in TMB-H patients (> 10 mut/Mb). "
            "Best response in endometrial (57%), cervical (46%), biliary (40%). "
            "FDA approval 2020 for TMB-H unresectable/metastatic solid tumours "
            "after progression on prior therapy. Excluded: colorectal cancer "
            "(TMB-H CRC responds poorly to PD-1 alone without MSI-H)."
        ),
        topic_tags=["clinical_trial", "pembrolizumab", "tmb", "keynote-158", "immunotherapy"],
        confidence=0.94,
        knowledge_type=MedicalKnowledgeType.CLINICAL_TRIAL,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.90,
    ),

    _SeedEntry(
        content=(
            "POLO trial (olaparib maintenance, germline BRCA-mutated metastatic pancreatic cancer): "
            "mPFS 7.4 months vs 3.8 months (HR 0.53, p=0.004) vs placebo. "
            "FDA approval 2019; first targeted therapy for BRCA-mutated pancreatic cancer. "
            "Eligibility: germline BRCA1/2 mutation + metastatic pancreatic cancer + "
            "at least 16 weeks of platinum-based first-line therapy without progression."
        ),
        topic_tags=["clinical_trial", "olaparib", "brca", "pancreatic_cancer", "parp_inhibitor"],
        confidence=0.91,
        knowledge_type=MedicalKnowledgeType.CLINICAL_TRIAL,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.PANCREATIC,
        clinical_significance=0.88,
        patient_population="Germline BRCA1/2-mutated metastatic pancreatic cancer",
    ),

    # ------------------------------------------------------------------
    # Prognostic / staging frameworks
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "TNM staging system: T (tumour extent), N (nodal involvement), M (distant metastasis). "
            "Stage I (localised) through Stage IV (metastatic). "
            "Example 5-year overall survival by stage (breast cancer): "
            "Stage I ~99%, Stage II ~86%, Stage III ~72%, Stage IV ~28%. "
            "Accurate staging requires pathological assessment plus cross-sectional imaging. "
            "Used for treatment planning, clinical trial eligibility, and prognosis communication."
        ),
        topic_tags=["staging", "tnm", "prognosis", "guideline"],
        confidence=0.97,
        knowledge_type=MedicalKnowledgeType.GUIDELINE,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.97,
    ),

    # ------------------------------------------------------------------
    # Testing / guideline panels
    # ------------------------------------------------------------------

    _SeedEntry(
        content=(
            "Comprehensive oncology biomarker testing (NGS recommended): "
            "Advanced NSCLC — must include EGFR, ALK, ROS1, BRAF, MET, RET, KRAS G12C, NTRK fusions, "
            "HER2, TMB, MSI. "
            "Advanced breast cancer — HER2, BRCA1/2, PIK3CA, ESR1 (liquid biopsy on progression). "
            "Advanced CRC — RAS (KRAS/NRAS), BRAF V600E, MSI/dMMR, HER2. "
            "Melanoma — BRAF V600E/K, NRAS, c-KIT. "
            "Concurrent tissue and liquid biopsy maximise detection yield."
        ),
        topic_tags=["ngs", "biomarker", "panel_testing", "genomics", "guideline"],
        confidence=0.95,
        knowledge_type=MedicalKnowledgeType.GUIDELINE,
        evidence_level=ClinicalEvidenceLevel.SYSTEMATIC_REVIEW,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.96,
    ),

    _SeedEntry(
        content=(
            "Palliative care integration in oncology: early concurrent palliative care "
            "alongside standard oncology care reduces aggressive end-of-life interventions, "
            "improves quality of life (FACT-L, ESAS scores) and patient-reported outcomes. "
            "Survival benefit observed in advanced NSCLC (Temel et al., NEJM 2010). "
            "ASCO recommends palliative care integration within 8 weeks of advanced cancer diagnosis. "
            "Goals-of-care discussions should begin at diagnosis in Stage IV disease."
        ),
        topic_tags=["palliative_care", "quality_of_life", "supportive_care", "patient_outcomes",
                    "guideline"],
        confidence=0.89,
        knowledge_type=MedicalKnowledgeType.GUIDELINE,
        evidence_level=ClinicalEvidenceLevel.RCT,
        oncology_domain=OncologyDomain.GENERAL,
        clinical_significance=0.88,
    ),
]


def seed_mouseion(
    mouseion: "Mouseion",
    verbose: bool = False,
) -> list[tuple[KnowledgeRecordV0, MedicalKnowledgeRecordV0]]:
    """
    Pre-populate the Mouseion substrate with established oncological knowledge.

    Creates paired records: a core ``KnowledgeRecordV0`` (in the Mouseion)
    and a ``MedicalKnowledgeRecordV0`` (domain metadata) for each seed entry.

    Parameters
    ----------
    mouseion:
        The Mouseion substrate instance to seed.
    verbose:
        If True, log each record as it is stored.

    Returns
    -------
    list of (KnowledgeRecordV0, MedicalKnowledgeRecordV0) pairs
        The newly created records, for downstream inspection.
    """
    pairs: list[tuple[KnowledgeRecordV0, MedicalKnowledgeRecordV0]] = []

    for entry in _SEED_ENTRIES:
        # Determine effective confidence using evidence level weight
        effective_confidence = min(
            1.0,
            entry.confidence * entry.evidence_level.confidence_weight,
        )

        # Store in Mouseion knowledge base
        base_record = mouseion.store_knowledge(
            author_id=EXMORBUS_SEED_AUTHOR,
            content=entry.content,
            topic_tags=entry.topic_tags,
            confidence=effective_confidence,
        )

        # Create the domain metadata companion record
        medical_meta = MedicalKnowledgeRecordV0(
            base_record_id=base_record.record_id,
            knowledge_type=entry.knowledge_type,
            evidence_level=entry.evidence_level,
            oncology_domain=entry.oncology_domain,
            patient_population=entry.patient_population,
            clinical_significance=entry.clinical_significance,
            guideline_aligned=True,
            review_status="validated",
        )
        pairs.append((base_record, medical_meta))

        if verbose:
            logger.info(
                "Seeded: [%s/%s] %.2f confidence — %s",
                entry.knowledge_type.value,
                entry.oncology_domain.value,
                effective_confidence,
                entry.content[:60],
            )

    logger.info(
        "ExMorbus seeder: %d oncological knowledge records loaded into Mouseion",
        len(pairs),
    )
    return pairs


def seed_summary(pairs: list[tuple[KnowledgeRecordV0, MedicalKnowledgeRecordV0]]) -> dict:
    """Return a summary dict of seeded records for diagnostics."""
    from collections import Counter
    type_counts: Counter = Counter()
    domain_counts: Counter = Counter()
    total_confidence = 0.0

    for base, meta in pairs:
        type_counts[meta.knowledge_type.value] += 1
        domain_counts[meta.oncology_domain.value] += 1
        total_confidence += base.confidence

    return {
        "total_records": len(pairs),
        "mean_confidence": round(total_confidence / max(len(pairs), 1), 3),
        "by_type": dict(type_counts),
        "by_domain": dict(domain_counts),
    }
