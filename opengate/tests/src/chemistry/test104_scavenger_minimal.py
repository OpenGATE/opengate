#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from box import Box
import opengate as gate
import opengate_core as g4
from opengate.tests import utility

SCAVENGER_SIGNATURE_CONFIG_NAMES = ["HO_2°"]
SCAVENGER_TRACKED_COUNTER_SPECIES = ["O2m", *SCAVENGER_SIGNATURE_CONFIG_NAMES]
SCAVENGER_MOLECULE_COUNTER_NAMES = ["HO_2°"]
SCAVENGER_SIGNATURE_RUNTIME_NAMES = ["O_2^-1", "HO_2°^0"]
E_AQ_CONFIG_NAME = "e_aq"
E_AQ_RUNTIME_NAME = "e_aq^-1"
REALISTIC_O2_EAQ_RATE_CONSTANT_DM3_PER_MOLE_S = 1.74e10
# Boost the rate in this test so the scavenger effect is easier to observe in a
# compact setup. Keep the realistic value above as documentation because users
# often refer to tests as examples.
TEST_O2_EAQ_RATE_CONSTANT_DM3_PER_MOLE_S = 1.74e13


def dump_scavenger_processes(simulation_engine):
    scheduler = g4.G4Scheduler.Instance()
    scavenger_material = scheduler.GetScavengerMaterial()
    if scavenger_material is not None:
        scavenger_material.SetCounterAgainstTime()

    chemistry_world = simulation_engine.simulation.chemistry_manager.chemistry_world
    tracked_names = []
    if chemistry_world is not None:
        tracked_names = sorted(
            {
                reaction.tracked_molecule
                for reaction in chemistry_world.scavenger_reactions
            }
        )

    process_dump = {}
    molecule_table = (
        simulation_engine.chemistry_engine.chemistry_manager.chemistry_list.g4_molecule_table
    )
    for tracked_name in tracked_names:
        tracked_conf = molecule_table.GetConfiguration(tracked_name, False)
        definition_name = None
        process_names = []
        if tracked_conf is not None:
            tracked_definition = tracked_conf.GetDefinition()
            definition_name = tracked_definition.GetParticleName()
            process_manager = tracked_definition.GetProcessManager()
            if process_manager is not None:
                process_vector = process_manager.GetProcessList()
                if process_vector is not None:
                    for i in range(process_vector.size()):
                        process_names.append(process_vector[i].GetProcessName())
        process_dump[tracked_name] = {
            "definition": definition_name,
            "processes": process_names,
        }

    simulation_engine.user_hook_log = Box(
        {
            "tracked_processes": process_dump,
            "scavenger_material": (
                None
                if scavenger_material is None
                else {
                    "species": list(scavenger_material.GetScavengerNames()),
                    "initial_O2_count": scavenger_material.GetSpeciesCount("O2"),
                }
            ),
        }
    )


def collect_scavenger_material_after_run(simulation_engine):
    scheduler = g4.G4Scheduler.Instance()
    scavenger_material = scheduler.GetScavengerMaterial()
    if (
        not hasattr(simulation_engine, "user_hook_log")
        or simulation_engine.user_hook_log is None
    ):
        simulation_engine.user_hook_log = Box()
    if scavenger_material is None:
        simulation_engine.user_hook_log["scavenger_material_after_run"] = None
        return
    simulation_engine.user_hook_log["scavenger_material_after_run"] = {
        "species": list(scavenger_material.GetScavengerNames()),
        "final_O2_count": scavenger_material.GetSpeciesCount("O2"),
    }


def create_simulation(enable_scavenger):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456
    sim.number_of_threads = 1

    km = gate.g4_units.km
    um = gate.g4_units.um
    keV = gate.g4_units.keV
    m3 = gate.g4_units.m3
    mole = gate.g4_units.mole
    liter = gate.g4_units.liter
    s = gate.g4_units.s

    sim.world.size = [1 * km, 1 * km, 1 * km]
    sim.world.material = "G4_WATER"

    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"
    sim.chemistry_manager.time_step_model = "SBS"

    target = sim.add_volume("Box", "chem_box")
    # Keep the oxygen reservoir as small as possible while still containing the
    # full electron track. A 1 keV electron started at the center of this water
    # box should stay well within the 10 um half-side in this test geometry.
    target.size = [20 * um, 20 * um, 20 * um]
    target.material = "G4_WATER"
    target.set_track_structure_em_physics("G4EmDNAPhysics_option2")

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 1 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "iso"
    source.n = 200

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    chem_actor = sim.add_actor("ChemicalStageActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 50
    # This test targets the scavenger-driven molecule production path. The
    # built-in reaction counter currently trips over a separate time-ordering
    # issue once scavenger reactions become active, so keep it out of the way
    # here and validate the scavenger feature through the molecule counter.
    chem_actor.counters.reaction_counter.active = False
    # Geant4-DNA configuration identifiers such as "O2m" are exposed through
    # runtime molecule names carrying the charge state. In this setup, the
    # scavenger signature can show up either as the transient superoxide
    # species or as the follow-up hydroperoxyl radical.
    chem_actor.counters.molecule_counter.consider_molecules = [
        E_AQ_CONFIG_NAME,
        *SCAVENGER_MOLECULE_COUNTER_NAMES,
    ]

    if enable_scavenger:
        chemistry_world = sim.chemistry_manager.create_chemistry_world(volume=target)
        chemistry_world.pH = 7
        chemistry_world.add_component("O2", 2.5e-2 * mole / liter)
        dm3_per_mole_s = 1e-3 * m3 / (mole * s)
        chemistry_world.add_scavenger_reaction(
            tracked_molecule="e_aq",
            scavenger="O2",
            products=["O2m"],
            rate_constant=TEST_O2_EAQ_RATE_CONSTANT_DM3_PER_MOLE_S * dm3_per_mole_s,
        )
        chem_actor.counters.configured_species_counter.tracked_species = (
            SCAVENGER_TRACKED_COUNTER_SPECIES
        )
        chem_actor.counters.configured_species_counter.active = True
        sim.user_hook_after_init = dump_scavenger_processes
        sim.user_hook_after_run = collect_scavenger_material_after_run

    return sim, stats, chem_actor


def get_peak_count(series_dict, labels):
    peak_count = 0
    for label in labels:
        series = series_dict.get(label)
        if series is not None and len(series) > 0:
            peak_count = max(peak_count, int(series["count"].max()))
    return peak_count


def get_final_count(series_dict, labels):
    final_count = 0
    for label in labels:
        series = series_dict.get(label)
        if series is not None and len(series) > 0:
            final_count = max(final_count, int(series["count"][-1]))
    return final_count


if __name__ == "__main__":
    sim_ref, stats_ref, chem_actor_ref = create_simulation(enable_scavenger=False)
    sim_ref.run(start_new_process=True)

    sim_scav, stats_scav, chem_actor_scav = create_simulation(enable_scavenger=True)
    sim_scav.run(start_new_process=False)

    ref_results = chem_actor_ref.results.get_data()
    scav_results = chem_actor_scav.results.get_data()
    ref_counter = chem_actor_ref.molecule_counter.get_data()
    scav_counter = chem_actor_scav.molecule_counter.get_data()
    scavenger_species_counter = chem_actor_scav.configured_species_counter.get_data()

    ref_o2m_peak = get_peak_count(ref_counter, SCAVENGER_SIGNATURE_RUNTIME_NAMES)
    scav_o2m_peak = get_peak_count(scav_counter, SCAVENGER_SIGNATURE_RUNTIME_NAMES)
    ref_eaq_peak = get_peak_count(ref_counter, [E_AQ_RUNTIME_NAME])
    scav_eaq_peak = get_peak_count(scav_counter, [E_AQ_RUNTIME_NAME])
    scavenger_signature_appearances = get_final_count(
        scavenger_species_counter, SCAVENGER_TRACKED_COUNTER_SPECIES
    )
    initial_o2_count = sim_scav.user_hook_log.scavenger_material["initial_O2_count"]
    final_o2_count = sim_scav.user_hook_log.scavenger_material_after_run[
        "final_O2_count"
    ]

    print("Baseline run without scavenger")
    print(f"  events: {stats_ref.counts.events}")
    print(f"  chemistry_starts: {ref_results.chemistry_starts}")
    print(f"  reaction_count: {ref_results.reaction_count}")
    print(f"  peak e_aq population: {ref_eaq_peak}")
    print(f"  peak oxygen-scavenger signature population: {ref_o2m_peak}")

    print("Run with O2 scavenger")
    print(f"  events: {stats_scav.counts.events}")
    print(f"  chemistry_starts: {scav_results.chemistry_starts}")
    print(f"  reaction_count: {scav_results.reaction_count}")
    print(f"  peak e_aq population: {scav_eaq_peak}")
    print(f"  peak oxygen-scavenger signature population: {scav_o2m_peak}")
    print(
        f"  cumulative tracked scavenger-signature appearances: {scavenger_signature_appearances}"
    )
    print(f"  initial O2 reservoir population: {initial_o2_count}")
    print(f"  final O2 reservoir population: {final_o2_count}")

    is_ok = True
    is_ok = is_ok and ref_results.chemistry_starts > 0
    is_ok = is_ok and scav_results.chemistry_starts > 0
    is_ok = is_ok and sim_scav.user_hook_log.scavenger_material is not None
    is_ok = is_ok and "O_2^0" in sim_scav.user_hook_log.scavenger_material["species"]
    is_ok = is_ok and scavenger_signature_appearances > 0
    is_ok = is_ok and final_o2_count < initial_o2_count

    utility.test_ok(is_ok)
