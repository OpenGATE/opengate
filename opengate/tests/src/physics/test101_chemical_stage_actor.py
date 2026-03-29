#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate
from opengate.tests import utility


def print_results(label, results):
    print(label)
    print(f"  recorded_events: {results.recorded_events}")
    print(f"  chemistry_starts: {results.chemistry_starts}")
    print(f"  chemistry_stages: {results.chemistry_stages}")
    print(f"  pre_time_step_calls: {results.pre_time_step_calls}")
    print(f"  post_time_step_calls: {results.post_time_step_calls}")
    print(f"  reaction_count: {results.reaction_count}")
    print(f"  killed_particles: {results.killed_particles}")
    print(f"  aborted_events: {results.aborted_events}")
    print(
        f"  accumulated_primary_energy_loss: {results.accumulated_primary_energy_loss}"
    )
    print(f"  total_energy_deposit: {results.total_energy_deposit}")
    print(f"  mean_restricted_let: {results.mean_restricted_let}")
    print(f"  std_restricted_let: {results.std_restricted_let}")
    print(f"  chemistry_times: {len(results.times_to_record)}")
    print(f"  species_times: {len(results.species)}")


def create_simulation(use_actor_requested_dna_em):
    sim = gate.Simulation()

    sim.g4_verbose = False
    sim.visu = False
    sim.random_engine = "MersenneTwister"
    sim.random_seed = 123456
    sim.number_of_threads = 1

    km = gate.g4_units.km
    um = gate.g4_units.um
    keV = gate.g4_units.keV

    sim.world.size = [1 * km, 1 * km, 1 * km]
    sim.world.material = "G4_WATER"

    # chem6 default pair
    sim.physics_manager.physics_list_name = "G4EmStandardPhysics"
    sim.chemistry_manager.chemistry_list_name = "G4EmDNAChemistry_option3"

    # Small inner water box representing the local chemistry/scoring region.
    target = sim.add_volume("Box", "chem_box")
    target.size = [10 * um, 10 * um, 10 * um]
    target.material = "G4_WATER"

    if not use_actor_requested_dna_em:
        # Explicit region-based DNA EM configured on the target volume.
        target.set_dna_em_physics("DNA_Opt2")

    source = sim.add_source("GenericSource", "source")
    source.particle = "e-"
    source.energy.mono = 2 * keV
    source.position.type = "point"
    source.position.translation = [0, 0, 0]
    source.direction.type = "momentum"
    source.direction.momentum = [0, 0, 1]
    source.n = 1

    stats = sim.add_actor("SimulationStatisticsActor", "stats")

    chem_actor = sim.add_actor("ChemicalStageActor", "chem_actor")
    chem_actor.attached_to = target
    chem_actor.number_of_time_bins = 50
    if use_actor_requested_dna_em:
        chem_actor.dna_em_physics = "DNA_Opt2"
    else:
        chem_actor.dna_em_physics = None

    return sim, stats, chem_actor


def check_single_run(stats, results):
    is_ok = True

    print_results("Checking ChemicalStageActor output:", results)

    is_ok = is_ok and stats.counts.events == 1
    is_ok = is_ok and results.chemistry_starts == 1
    is_ok = is_ok and results.recorded_events == 1
    is_ok = is_ok and results.chemistry_stages >= 1
    is_ok = is_ok and results.pre_time_step_calls > 0
    is_ok = is_ok and results.post_time_step_calls > 0
    is_ok = is_ok and len(results.times_to_record) == 50
    is_ok = is_ok and len(results.species) > 0
    is_ok = is_ok and results.total_energy_deposit >= 0.0
    is_ok = is_ok and results.accumulated_primary_energy_loss >= 0.0
    is_ok = is_ok and results.reaction_count >= 0

    return is_ok


def _species_signature(species_dict):
    signature = {}
    for time, species_at_time in species_dict.items():
        signature[float(time)] = {}
        for species_name, values in species_at_time.items():
            signature[float(time)][str(species_name)] = (
                int(values["number"]),
                float(values["sum_g"]),
                float(values["sum_g2"]),
            )
    return signature


def compare_results(result1, result2):
    is_ok = True

    same_fields = [
        "killed_particles",
        "aborted_events",
        "chemistry_starts",
        "chemistry_stages",
        "pre_time_step_calls",
        "post_time_step_calls",
        "reaction_count",
        "recorded_events",
        "accumulated_primary_energy_loss",
        "total_energy_deposit",
        "mean_restricted_let",
        "std_restricted_let",
        "times_to_record",
        "reactions",
    ]

    print("Comparing chemistry results:")
    for field in same_fields:
        value1 = result1[field]
        value2 = result2[field]
        print(f"{field}: {value1} / {value2}")
        is_ok = is_ok and value1 == value2

    species1 = _species_signature(result1["species"])
    species2 = _species_signature(result2["species"])
    print("species signature identical:", species1 == species2)
    is_ok = is_ok and species1 == species2

    return is_ok


if __name__ == "__main__":
    sim_global, stats_global, chem_actor_global = create_simulation(
        use_actor_requested_dna_em=False
    )
    sim_global.run(start_new_process=True)
    results_global = chem_actor_global.results.get_data()
    print_results("Explicit region DNA EM results:", results_global)

    sim_actor, stats_actor, chem_actor_actor = create_simulation(
        use_actor_requested_dna_em=True
    )
    sim_actor.run(start_new_process=True)
    results_actor = chem_actor_actor.results.get_data()
    print_results("Actor-requested DNA EM results:", results_actor)

    is_ok = check_single_run(stats_global, results_global)
    is_ok = check_single_run(stats_actor, results_actor) and is_ok
    is_ok = compare_results(results_global, results_actor) and is_ok

    utility.test_ok(is_ok)
