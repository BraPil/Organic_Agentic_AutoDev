"""
examples/medical_ecosystem.py

ExMorbus Medical Oncology Research Ecosystem — full end-to-end demonstration.

This script demonstrates the complete organic agentic architecture applied to
a medical/oncological research context:

  1. The Mouseion substrate is seeded with 20 established oncological knowledge
     records (genomics, treatment protocols, adverse events, imaging criteria).

  2. Twelve oncology-specific niches are opened — urgent clinical tasks that
     need specialist agents to fill them (GUARDIAN, PATHOLOGIST, ONCOLOGIST,
     GENETICIST, RADIOLOGIST, etc.).

  3. A colony of StemCells is spawned with genomes biased toward medical roles.
     Each cell begins as a blank slate and differentiates into its specialist
     role as niche signals accumulate.

  4. Differentiated cells form a Tumor Board organ (ONCOLOGIST + PATHOLOGIST +
     GENETICIST + RADIOLOGIST cluster), which the Body integrates into a
     holistic oncological intelligence.

  5. The SLITracker monitors compliance with the Medical Ecosystem SLA in real
     time, reporting which SLOs are meeting, at risk, or breached each tick.

  6. The slime mold network evolves adaptively — paths between collaborating
     specialist cells strengthen, unused connections decay.

Usage:
    python examples/medical_ecosystem.py

Output:
    - Per-tick tick summary (agent count, niches filled, knowledge records)
    - SLI dashboard every 10 ticks
    - Final Body vision statement
    - Final SLA compliance report
"""

from __future__ import annotations

import logging
import random
import sys

# Suppress verbose substrate logging for a cleaner output
logging.getLogger("mouseion.substrate").setLevel(logging.WARNING)
logging.getLogger("environment").setLevel(logging.WARNING)
logging.getLogger("exmorbus.seeder").setLevel(logging.WARNING)
logging.getLogger("observability.tracker").setLevel(logging.WARNING)
logging.getLogger("stem_cell").setLevel(logging.WARNING)
logging.getLogger("cell").setLevel(logging.WARNING)
logging.getLogger("organ").setLevel(logging.WARNING)
logging.getLogger("body").setLevel(logging.WARNING)

from src.core.environment import Environment
from src.core.stem_cell import StemCell
from src.domain.exmorbus import create_medical_genome, create_medical_niches, seed_mouseion
from src.domain.exmorbus.seeder import seed_summary
from src.mouseion.contracts import AgentRole, ResourceKind
from src.mouseion.substrate import Mouseion
from src.observability import SLITracker, build_medical_sla
from src.organisms.body import Body
from src.organisms.cell import Cell
from src.organisms.organ import Organ
from src.slime_mold.network import SlimeMoldNetwork


def print_header(title: str) -> None:
    bar = "═" * 70
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def print_section(title: str) -> None:
    print(f"\n  ── {title} ──")


def run_medical_ecosystem(
    n_stem_cells: int = 24,
    n_ticks: int = 80,
    seed: int = 42,
) -> None:
    rng = random.Random(seed)

    print_header("🧬  ExMorbus Medical Oncology Research Ecosystem")
    print(f"  Stem cells: {n_stem_cells} | Ticks: {n_ticks} | Seed: {seed}")

    # ----------------------------------------------------------------
    # 1. Initialise substrate
    # ----------------------------------------------------------------
    print_section("Initialising Mouseion substrate")
    mouseion = Mouseion(initial_resources={
        ResourceKind.ENERGY: 2000.0,
        ResourceKind.COMPUTE: 800.0,
        ResourceKind.DATA: 1200.0,
        ResourceKind.ATTENTION: 400.0,
        ResourceKind.KNOWLEDGE: 600.0,
        ResourceKind.TRUST: 300.0,
    })
    env = Environment(mouseion=mouseion, neighbourhood_radius=20, rng=rng)

    # ----------------------------------------------------------------
    # 2. Seed the Mouseion with ExMorbus oncological knowledge
    # ----------------------------------------------------------------
    print_section("Seeding Mouseion with ExMorbus oncological knowledge")
    pairs = seed_mouseion(mouseion)
    summary = seed_summary(pairs)
    print(f"  ✓ {summary['total_records']} knowledge records loaded "
          f"(mean confidence: {summary['mean_confidence']:.3f})")
    print(f"  ✓ Knowledge types: {', '.join(summary['by_type'].keys())}")
    print(f"  ✓ Oncology domains: {', '.join(summary['by_domain'].keys())}")

    # ----------------------------------------------------------------
    # 3. Open oncological niches
    # ----------------------------------------------------------------
    print_section("Opening oncology niches (clinical task board)")
    niches = create_medical_niches()
    env.seed_niches(niches)
    for niche in sorted(niches, key=lambda n: -n.urgency)[:5]:
        print(f"  [{niche.urgency:.2f}] {niche.role.value:<22} — {niche.description[:55]}…")
    print(f"  … and {len(niches) - 5} more niches")

    # ----------------------------------------------------------------
    # 4. Initialise the SlimeMold network
    # ----------------------------------------------------------------
    network = SlimeMoldNetwork(rng=rng)

    # ----------------------------------------------------------------
    # 5. Spawn StemCells with medically-biased genomes
    # ----------------------------------------------------------------
    print_section(f"Spawning {n_stem_cells} medical StemCells")
    medical_roles = [
        AgentRole.ONCOLOGIST, AgentRole.PATHOLOGIST, AgentRole.CLINICAL_TRIALIST,
        AgentRole.GENETICIST, AgentRole.PHARMACOLOGIST, AgentRole.RADIOLOGIST,
        AgentRole.PATIENT_ADVOCATE, AgentRole.EPIDEMIOLOGIST,
    ]
    stem_cells: list[StemCell] = []
    for i in range(n_stem_cells):
        # Cycle through medical roles with some diversity
        bias_role = medical_roles[i % len(medical_roles)]
        genome = create_medical_genome(bias_role, rng=rng)
        cell = StemCell(genome=genome, initial_energy=25.0, rng=random.Random(rng.randint(0, 99999)))
        env.register(cell)
        stem_cells.append(cell)
    print(f"  ✓ {n_stem_cells} StemCells registered (genomes biased toward medical specialties)")

    # ----------------------------------------------------------------
    # 6. Initialise SLA tracker
    # ----------------------------------------------------------------
    print_section("Activating SLA / SLO / SLI tracker")
    sla = build_medical_sla()
    body = Body("ExMorbus Oncology Intelligence")
    tracker = SLITracker(
        mouseion=mouseion,
        environment=env,
        sla=sla,
        body=body,
        initial_energy=2000.0,
    )
    body.attach_to_network(network)
    print(f"  ✓ SLA '{sla.name}' active with {len(sla.slos)} SLOs")

    # ----------------------------------------------------------------
    # 7. Run simulation
    # ----------------------------------------------------------------
    print_header("🔬  Running Medical Ecosystem Simulation")
    differentiations: dict[str, int] = {}   # role → count
    organs_formed: list[Organ] = []
    last_cluster_tick = 0

    for tick in range(1, n_ticks + 1):
        env.tick()
        network.tick()
        tracker_report = tracker.tick()

        # Track newly differentiated cells
        for cell in env.all_agents():
            if cell.is_differentiated and cell.role.value not in differentiations:
                differentiations[cell.role.value] = tick

        # Attempt organ formation every 15 ticks from differentiated cells
        if tick % 15 == 0 and tick != last_cluster_tick:
            clusters = network.detect_clusters(min_conductance=0.05)
            formed_this_round = 0
            for cluster in clusters:
                candidate_ids = list(cluster)
                candidate_cells = [
                    a for a in env.all_agents()
                    if a.agent_id in candidate_ids and a.is_differentiated
                    and getattr(a, "organ_id", None) is None
                ]
                if len(candidate_cells) >= 2:
                    # Only form an organ if not all cells already have one
                    fresh = [c for c in candidate_cells if not hasattr(c, '_organ_id') or c._organ_id is None]
                    if len(fresh) >= 2:
                        organ = Organ(founding_cells=fresh[:6])  # cap at 6 founding cells
                        for fc in fresh[:6]:
                            network.add_agent(organ.organ_id, role=organ.dominant_role.value)
                        body.register_organ(organ)
                        organs_formed.append(organ)
                        formed_this_round += 1
                        last_cluster_tick = tick
                        break   # one organ per organ-formation round

        # Periodic progress output
        if tick % 10 == 0:
            alive = env.agent_count()
            kc = mouseion.knowledge_count()
            open_n = len(env.open_niches())
            filled_n = len(niches) - open_n
            print(
                f"  Tick {tick:3d} | Agents: {alive:3d} | "
                f"Knowledge: {kc:3d} | Niches: {filled_n}/{len(niches)} filled | "
                f"Organs: {len(organs_formed)}"
            )
            if tracker_report["breached_slos"]:
                print(f"         ⚠️  SLO Breach: {', '.join(tracker_report['breached_slos'])}")
            if tick % 30 == 0:
                print(tracker.dashboard_string())

    # ----------------------------------------------------------------
    # 8. Post-simulation results
    # ----------------------------------------------------------------
    print_header("📊  Simulation Results")

    print_section("Differentiation outcomes")
    if differentiations:
        for role, t in sorted(differentiations.items(), key=lambda x: x[1]):
            print(f"  {role:<25} differentiated at tick {t}")
    else:
        print("  No differentiations recorded (increase n_ticks or lower thresholds)")

    print_section("Organs formed")
    if organs_formed:
        for organ in organs_formed:
            print(f"  {organ}")
    else:
        print("  No organs formed this run (more ticks or more network activity needed)")

    if body.is_fully_functional:
        print_section("Body vision")
        vision = body.latest_vision
        if vision:
            print(f"  [{vision.vision_id[:8]}] confidence={vision.confidence:.2f}")
            print(f"  \"{vision.statement[:200]}…\"")

    print_section("Mouseion knowledge summary")
    final_kc = mouseion.knowledge_count()
    print(f"  Total records: {final_kc} (seeded: 20, agent-produced: {final_kc - 20})")
    resource_summary = mouseion.resource_summary()
    energy_remaining = resource_summary["energy"]["available"]
    print(f"  Energy pool remaining: {energy_remaining:.0f} / 2000.0 "
          f"({energy_remaining/2000*100:.1f}%)")

    print_section("Final SLA compliance report")
    print(tracker.dashboard_string())

    compliance = tracker.compliance_summary()
    print(f"\n  {'✅ SLA COMPLIANT' if compliance['sla_compliant'] else '🔴 SLA NON-COMPLIANT'}")
    print(f"  {compliance['meeting']}/{compliance['total_slos']} SLOs meeting "
          f"(target: {sla.compliance_target:.0%})\n")


if __name__ == "__main__":
    run_medical_ecosystem(
        n_stem_cells=24,
        n_ticks=80,
        seed=42,
    )
